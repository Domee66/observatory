To run the script, you’ll need to follow these steps:

### 1. **Prepare Your Environment**

Before running the script, ensure that the necessary dependencies and services are installed and configured.

#### **1.1. Install Required Python Packages**

Make sure Python is installed on your system. If not, you can install it via your package manager (e.g., `sudo apt-get install python3` on Ubuntu).

Next, install the required Python packages using `pip`:

```bash
pip install pyindi-client astroquery astropy
```

#### **1.2. Set Up INDI Server**

Ensure the INDI server is installed and running. You can install it using:

```bash
sudo apt-get install indi-full
```

Start the INDI server:

```bash
indiserver -v indi_ioptron_telescope indi_asi_ccd indi_asi_wheel
```

Replace the device names with the ones corresponding to your hardware. The `-v` flag is for verbose mode, which helps in debugging.

#### **1.3. PHD2 Guiding Software**

Ensure PHD2 is installed and configured properly. You can install it using:

```bash
sudo apt-get install phd2
```

### 2. **Create the Script File**

Create a new Python script file:

```bash
nano observatory_control.py
```

Copy the entire script provided earlier into this file, then save and exit (`CTRL + X`, then `Y`, then `ENTER`).

### 3. **Run the Script**

To run the script, use the following command:

```bash
python3 observatory_control.py
```

### 4. **Using the Script**

After running the script, you can use the command functions within the script to control your observatory:

- **Example Commands**:
    - Turn the light off: 
      ```python
      observatory("set_light", state="off")
      ```
    - Start a sequence:
      ```python
      observatory("sequence", target="M42", base_directory="/images", filter_name="R", exposure_count=5, exposure_time=30)
      ```

### 5. **Automation & Scheduling**

If you want to automate tasks, consider using cron jobs:

- Open the crontab for editing:
  ```bash
  crontab -e
  ```

- Add a cron job to run the script at a specific time (e.g., every night at 10 PM):

  ```bash
  0 22 * * * /usr/bin/python3 /path/to/observatory_control.py
  ```

Replace `/path/to/observatory_control.py` with the actual path to your script.

### 6. **Monitoring & Logs**

The script logs activities to `/var/log/observatory_control.log`. You can monitor this file for any issues or to review the operation logs:

```bash
tail -f /var/log/observatory_control.log
```

### 7. **Testing & Debugging**

- **Start with Manual Commands**: Before fully automating, manually test the commands to ensure each device works as expected.
- **Logging**: Use the logs to troubleshoot any issues, especially with device connections or API responses.

### 8. **Make the Script Executable (Optional)**

You can make the script executable and run it directly from the command line:

```bash
chmod +x observatory_control.py
./observatory_control.py
```

By following these steps, you should be able to control your observatory equipment remotely and automate your observation sessions.
