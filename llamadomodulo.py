from PyHT6022.LibUsbScope import Oscilloscope
#    carpeta.nombrearchivo       clase
osc = Oscilloscope()
print ('PID: ', osc.PID)
print ('VID: ', osc.VID)
osc.setup()

if not osc.open_handle():
    print('conectalo burro!')
else:
    print('Estoy conectado!')
    if not osc.is_device_firmware_present:
        osc.flash_firmware()

if osc.open_handle():
    osc.close_handle()
