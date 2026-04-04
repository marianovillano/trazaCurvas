import os
import numpy as np
import torch
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from PIL import Image
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


def cosine_similarity(v1, v2):
    """Calculates the cosine similarity between two vectors (-1.0 to 1.0)"""
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def train_mode(device, model_path, path_samples):
    
    # 1. Load Feature Extractor
    model = load_mobilenet(device)

    # 2. Load Data
    ref_dir = os.path.join(path_samples)
    print(f"\n--- TRAINING MODE: Learning from {ref_dir} ---")
    ref_images = scan_directory(ref_dir)

    if not ref_images:
        print("No reference images inserted")
        return

    ref_embeddings, ref_paths = get_image_embeddings(model, ref_images, device)

    # 3. Build Reference Dictionary
    print("Building reference dictionary (1-to-1 pin matching)...")
    reference_db = {}
    
    for emb, p in zip(ref_embeddings, ref_paths):
        path_obj = Path(p)
        ic_name = path_obj.parent.name
        pin_name = path_obj.stem
        
        pin_id = f"{ic_name}/{pin_name}"
        reference_db[pin_id] = emb

    # 4. Save Model
    print(f"Saving trained reference database to {model_path}...")
    joblib.dump(reference_db, model_path)
    print("Done!")


def test_mode(device, model_path, path_samples, threshold=0.95):
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found. Run with --train first or call with --model-name")
        return

    # 1. Load Feature Extractor
    model = load_mobilenet(device)

    # 2. Load Reference Dictionary
    print(f"Loading reference database from {model_path}...")
    reference_db = joblib.load(model_path)

    # 3. Load Data
    test_dir = os.path.join(path_samples)
    print(f"\n--- TESTING MODE: Scanning {test_dir} ---")
    test_images = scan_directory(test_dir)

    if not test_images:
        print("No test images found!")
        return

    test_embeddings, test_paths = get_image_embeddings(model, test_images, device)

    # 4. Predict (Compare 1-to-1)
    print("\n" + "=" * 50)
    print(f"FAULT DETECTION REPORT (Threshold: {threshold*100:.1f}%)")
    print("=" * 50)

    anomalies_found = 0
    unknown_pins = 0
    
    for emb, p in zip(test_embeddings, test_paths):
        path_obj = Path(p)
        ic_name = path_obj.parent.name
        pin_name = path_obj.stem
        
        pin_id = f"{ic_name}/{pin_name}"
        
        if pin_id not in reference_db:
            print(f"[UNKNOWN PIN] {ic_name} -> {pin_name} (No reference found in database!)")
            unknown_pins += 1
            continue
            
        ref_emb = reference_db[pin_id]
        sim = cosine_similarity(emb, ref_emb)
        
        if sim < threshold:
            anomalies_found += 1
            print(f"[ANOMALY DETECTED] {ic_name} -> {pin_name} (Match: {sim*100:.1f}%)")

    if anomalies_found == 0 and unknown_pins == 0:
        print("No anomalies detected. Board looks perfect!")
    elif anomalies_found == 0 and unknown_pins > 0:
        print("No anomalies detected in known pins, but some pins were missing in the reference.")
    else:
        print(f"\nTotal Anomalies Found: {anomalies_found}")


def main():
    parser = argparse.ArgumentParser(description="PCB Fault Detector AI (1-to-1 Pin Comparison)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--train', action='store_true', help='Extract signatures from Reference dataset')
    group.add_argument('--test', action='store_true', help='Test Suspect dataset against Reference')

    # Tuning arguments
    parser.add_argument('--threshold', type=float, default=0.98, 
                        help='Similarity threshold 0.0 to 1.0 (default: 0.98). Lower = Less Sensitive.')

    # Path and naming
    parser.add_argument('--path-samples', type=Path, required=True, 
                        help='With --train: Insert the path to save the Reference dataset. With --test: Insert the path of the Reference dataset')
    parser.add_argument('--model-name', type=str, required=False, default="no file name", 
                        help='Insert the name of the .joblib generated model with --train')
    args = parser.parse_args()

    device = get_device()
    
    truth_model_name = args.path_samples.name + ".joblib"
    full_path_and_name = os.path.join(args.path_samples, truth_model_name)
    print(f"Using Model Path: {full_path_and_name}")

    model_name = args.model_name
    
    if args.train:
        train_mode(device, full_path_and_name, path_samples=args.path_samples)
    elif args.test:
        test_mode(device, model_name, path_samples=args.path_samples, threshold=args.threshold)

if __name__ == "__main__":
    main()
