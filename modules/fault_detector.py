import os
import numpy as np
import torch
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from PIL import Image
from sklearn.svm import OneClassSVM
from pathlib import Path
import joblib
import argparse

try:
    import torch_directml
    _DIRECTML_AVAILABLE = True
except ImportError:
    _DIRECTML_AVAILABLE = False


def get_device():
    """Selects the best available compute device.
    Priority: DirectML (AMD/Intel GPU) > CUDA (Nvidia) > CPU
    """
    if _DIRECTML_AVAILABLE and torch_directml.device_count() > 0:
        device = torch_directml.device(0)
        name = torch_directml.device_name(0)
        print(f"Using DirectML GPU: {name}")
        return device
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
        return device
    else:
        print("Using CPU (no GPU acceleration available)")
        return torch.device("cpu")


def get_transform():
    """Returns the image transformation pipeline."""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def load_image(img_path, transform):
    """Loads and transforms an image."""
    try:
        img = Image.open(img_path).convert('RGB')
        return transform(img).unsqueeze(0)  # Add batch dimension
    except Exception as e:
        print(f"Error loading {img_path}: {e}")
        return None


def get_image_embeddings(model, image_paths, device):
    """Passes images through the model to get feature vectors."""
    embeddings = []
    valid_paths = []
    transform = get_transform()

    print(f"Extracting features from {len(image_paths)} images...")

    model.eval()
    with torch.no_grad():
        for p in image_paths:
            img_tensor = load_image(p, transform)
            if img_tensor is not None:
                img_tensor = img_tensor.to(device)

                # Forward pass
                # MobileNetV2 features before classifier
                features = model.features(img_tensor)
                # Global Average Pooling
                features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
                features = torch.flatten(features, 1)

                embeddings.append(features.cpu().numpy()[0])
                valid_paths.append(p)

    return np.array(embeddings), valid_paths


def scan_directory(root_dir):
    """Recursively finds all PNG images."""
    image_paths = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.png'):
                image_paths.append(os.path.join(root, file))
    return image_paths


def load_mobilenet(device):
    print("Loading MobileNetV2 feature extractor...")
    weights = MobileNet_V2_Weights.IMAGENET1K_V1
    model = mobilenet_v2(weights=weights)
    model.to(device)
    return model


def train_mode(device, model_path, path_samples, nu=0.01, gamma='scale'):
    
    # 1. Load Feature Extractor
    model = load_mobilenet(device)

    # 2. Load Data
    ref_dir = os.path.join(path_samples)
    print(f"\n--- TRAINING MODE: Learning from {ref_dir} ---")
    print(f"Hyperparameters: nu={nu}, gamma={gamma}")
    ref_images = scan_directory(ref_dir)

    if not ref_images:
        print("No reference images inserted")
        return

    ref_embeddings, _ = get_image_embeddings(model, ref_images, device)

    # 3. Train Anomaly Detector
    print("Training OneClassSVM...")
    # nu: Allow ~1% of training data to be outliers (similar to contamination)
    # gamma: Standard for RBF kernel
    clf = OneClassSVM(gamma=gamma, nu=nu, kernel='rbf')
    clf.fit(ref_embeddings)

    # 4. Save Model
    print(f"Saving trained model to {model_path}...")
    joblib.dump(clf, model_path)
    print("Done!")


def test_mode(device, model_path, path_samples):
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found. Run with --train first or call with --model-name")
        return

    # 1. Load Feature Extractor
    model = load_mobilenet(device)

    # 2. Load Anomaly Detector
    print(f"Loading trained model from {model_path}...")
    clf = joblib.load(model_path)

    # 3. Load Data
    test_dir = os.path.join(path_samples)
    print(f"\n--- TESTING MODE: Scanning {test_dir} ---")
    test_images = scan_directory(test_dir)

    if not test_images:
        print("No test images found!")
        return

    test_embeddings, test_paths = get_image_embeddings(model, test_images, device)

    # 4. Predict
    predictions = clf.predict(test_embeddings)
    scores = clf.decision_function(test_embeddings)

    # 5. Report
    print("\n" + "=" * 40)
    print("FAULT DETECTION REPORT")
    print("=" * 40)

    anomalies_found = 0
    for i, pred in enumerate(predictions):
        if pred == -1:
            anomalies_found += 1
            path_obj = Path(test_paths[i])
            ic_name = path_obj.parent.name
            pin_name = path_obj.stem
            score = scores[i]

            print(f"[ANOMALY DETECTED] {ic_name} -> {pin_name} (Score: {score:.5f})")

    if anomalies_found == 0:
        print("No anomalies detected. Board looks good!")
    else:
        print(f"\nTotal Anomalies Found: {anomalies_found}")


def main():
    parser = argparse.ArgumentParser(description="PCB Fault Detector AI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--train', action='store_true', help='Train on Reference dataset')
    group.add_argument('--test', action='store_true', help='Test on Suspect dataset')

    # Tuning arguments
    parser.add_argument('--nu', type=float, default=0.01, help='Sensitivity (default: 0.01). Lower = Less Sensitive.')
    parser.add_argument('--gamma', type=str, default='scale',
                        help='Kernel coefficient (default: scale). Try "auto" or float.')

    # Path and naming
    parser.add_argument('--path-samples', type=Path, required=True, help='Insert the path of the data captured or model')
    parser.add_argument('--model-name', type=str, required=False, default="no file name", help='Insert the name of the model')
    args = parser.parse_args()

    device = get_device()
    # device = torch.device("cpu")
    
    truth_model_name = args.path_samples.name + ".joblib"
    full_path_and_name = os.path.join(args.path_samples, truth_model_name)
    print(full_path_and_name)

    model_name = args.model_name
    print(f"The model name is: {model_name}")
    
    if args.train:
        train_mode(device, full_path_and_name, nu=args.nu, gamma=args.gamma, path_samples=args.path_samples)
    elif args.test:
        test_mode(device, model_name, path_samples=args.path_samples)


if __name__ == "__main__":
    main()
