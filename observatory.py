import time
import requests
import logging
import os
from datetime import datetime
from pyindi_client import PyINDI
from astropy.coordinates import SkyCoord, AltAz
from astroquery.simbad import Simbad
from astropy.time import Time
from astropy import units as u

# Setup logging
logging.basicConfig(filename='/var/log/observatory_control.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# INDI server configuration
INDI_SERVER_HOST = "localhost"
INDI_SERVER_PORT = 7624

# PHD2 API base URL
PHD2_API_URL = "http://localhost:4400"

# Initialize the INDI client
indi = PyINDI()
indi.set_server(INDI_SERVER_HOST, INDI_SERVER_PORT)

# Equipment settings
filters = {'L': 1, 'R': 2, 'G': 3, 'B': 4, 'H': 5, 'O': 6}
red_light_device = "Red Light"
telescope_cover_device = "Telescope Cover"
roof_device = "Observatory Roof"
focuser_device = "ZWO EAF"

# Utility Functions
def set_device_property(device, property_name, value):
    indi.send_new_switch(device, property_name, value)
    logging.info(f"Set {device} {property_name} to {value}")

def get_coordinates(object_name):
    simbad = Simbad()
    simbad.add_votable_fields('coordinates')
    result = simbad.query_object(object_name)
    
    if result:
        ra = result['RA'][0]
        dec = result['DEC'][0]
        coords = SkyCoord(f"{ra} {dec}", unit=(u.hourangle, u.deg))
        return coords
    else:
        logging.error(f"Object {object_name} not found.")
        return None

def check_altitude(coords):
    location = indi.get_device("iOptron IEQ Pro").get_property("GEOGRAPHIC_COORD").values
    observer_location = AltAz(location['LONG'], location['LAT'], location['ELEV'])
    alt_az = coords.transform_to(observer_location)
    altitude = alt_az.alt.degree
    return altitude

def slew_to_target(coords):
    indi.send_new_number("iOptron IEQ Pro", "EQUATORIAL_EOD_COORD", 
                         {"RA": coords.ra.deg, "DEC": coords.dec.deg})
    time.sleep(10)
    logging.info(f"Slewed to RA: {coords.ra.deg}, DEC: {coords.dec.deg}")

def start_guiding():
    response = requests.get(f"{PHD2_API_URL}/guide")
    return response.json().get('status') == 'OK'

def stop_guiding():
    response = requests.get(f"{PHD2_API_URL}/stop_capture")
    return response.json().get('status') == 'OK'

def enable_multi_star_guiding():
    response = requests.get(f"{PHD2_API_URL}/set_dec_guide_mode", params={'mode': 'multistar'})
    return response.json().get('status') == 'OK'

def capture_image(exposure_time, filter_name, directory, count):
    filter_position = filters[filter_name]
    indi.send_new_number("ZWO EFW", "FILTER_SLOT", "FILTER_SLOT_VALUE", filter_position)
    time.sleep(2)
    
    indi.send_new_number("ZWO CCD ASI183MM Pro", "CCD_EXPOSURE", "CCD_EXPOSURE_VALUE", exposure_time)
    time.sleep(exposure_time + 2)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%MUT')
    filename = f"{directory}/{filter_name}_{timestamp}_{count:04d}.fits"
    indi.send_new_text("ZWO CCD ASI183MM Pro", "CCD_SAVE", "CCD_SAVE_PATH", filename)
    logging.info(f"Captured {filename}")

def dither():
    indi.send_new_number("iOptron IEQ Pro", "TELESCOPE_MOTION_NS", "TELESCOPE_MOTION_NS_VALUE", 1)
    time.sleep(1)
    indi.send_new_number("iOptron IEQ Pro", "TELESCOPE_MOTION_WE", "TELESCOPE_MOTION_WE_VALUE", 1)
    time.sleep(1)
    indi.send_new_number("iOptron IEQ Pro", "TELESCOPE_MOTION_NS", "TELESCOPE_MOTION_NS_VALUE", 0)
    indi.send_new_number("iOptron IEQ Pro", "TELESCOPE_MOTION_WE", "TELESCOPE_MOTION_WE_VALUE", 0)

def focus():
    indi.send_new_number(focuser_device, "FOCUS_MOTION", "FOCUS_MOTION_VALUE", 1)
    time.sleep(2)
    indi.send_new_number(focuser_device, "FOCUS_MOTION", "FOCUS_MOTION_VALUE", 0)
    logging.info("Focusing complete.")

def create_directory(base_directory, target_name):
    timestamp = datetime.now().strftime('%Y%m%d_%H%MUT')
    directory_name = f"{base_directory}/{target_name}_{timestamp}"
    os.makedirs(directory_name, exist_ok=True)
    return directory_name

def check_continue_sequence(altitude):
    if altitude < 20:
        response = input(f"Target is at {altitude:.2f} degrees altitude, continue? (y/n): ")
        return response.lower() == 'y'
    return True

def show_image(directory, image_name):
    filepath = f"{directory}/{image_name}.fits"
    os.system(f"ds9 {filepath} &")

# Command Functions
def observatory_set_light(state):
    set_device_property(red_light_device, "LIGHT_STATE", state)

def observatory_telescope_cover(state):
    set_device_property(telescope_cover_device, "COVER_STATE", state)

def observatory_target(target_name):
    coords = get_coordinates(target_name)
    if coords:
        altitude = check_altitude(coords)
        if check_continue_sequence(altitude):
            slew_to_target(coords)
        else:
            logging.info("Aborted slew due to low altitude.")
    else:
        logging.error("Target not found.")

def observatory_sequence(target, base_directory, filter_name, exposure_count, exposure_time):
    coords = get_coordinates(target)
    if coords:
        altitude = check_altitude(coords)
        if check_continue_sequence(altitude):
            directory = create_directory(base_directory, target)
            enable_multi_star_guiding()
            start_guiding()
            for i in range(exposure_count):
                if i != 0:
                    dither()
                capture_image(exposure_time, filter_name, directory, i + 1)
            stop_guiding()
            logging.info(f"Sequence complete. Images stored in {directory}.")
        else:
            logging.info("Sequence aborted due to low altitude.")
    else:
        logging.error("Target not found.")

def observatory_focus():
    focus()

def observatory_showimage(directory, image_name):
    show_image(directory, image_name)

def observatory_roof(state):
    set_device_property(roof_device, "ROOF_STATE", state)

# Command Dispatcher
def observatory(command, **kwargs):
    commands = {
        "set_light": observatory_set_light,
        "telescope_cover": observatory_telescope_cover,
        "target": observatory_target,
        "sequence": observatory_sequence,
        "focus": observatory_focus,
        "showimage": observatory_showimage,
        "roof": observatory_roof,
    }
    
    if command in commands:
        commands[command](**kwargs)
    else:
        logging.error(f"Unknown command: {command}")

# Example usage
if __name__ == "__main__":
    # Example commands
    observatory("set_light", state="on")
    observatory("telescope_cover", state="off")
    observatory("target", target_name="M42")
    observatory("sequence", target="M42", base_directory="/images", filter_name="R", exposure_count=5, exposure_time=30)
    observatory("focus")
    observatory("showimage", directory="/images/M42_20240807_2230UT", image_name="M42_R_20240807_2230UT_0001")
    observatory("roof", state="open")
