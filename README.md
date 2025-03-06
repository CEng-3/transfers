# The Transfer Script(s)

## Setup

### stream.py

Make sure that the camera is connected to the Raspberry Pi and verify it by **opening a Terminal window and entering the `rpicam-hello` command**. If you connected the camera after turning on the Raspberry Pi, it most likely needs to be restarted for the camera to start working.

1. Update the Raspberry Pi and install Git

```
sudo apt update && sudo apt upgrade -y && sudo apt install git -y
```

2. Change directory to the home directory and clone the GitHub repository

```
cd
git clone https://github.com/CEng-3/transfers.git
```

3. After Git has cloned the repository, change into the directory

```
cd site
```

4. Create a virtual environment

```
python3 -m venv venv
```

5. Install OpenCV as a system package

```
sudo apt-get install -y python3-opencv
```

6. Create a symbolic link

```
cd venv/lib/python3*/site-packages/
ln -s /usr/lib/python3/dist-packages/cv2.* .
```

7. Run

```
python3 stream.py
```

## Updating

You should **clone this repository on the Raspberry Pi** and then also **clone the repository on your local machine.** You should make changes on your local machine, commit them, and then test them on the Raspberry Pi.

1. Change into the repository directory

```
cd site
```

2. Use Git to update the version on the machine

```
git pull
```

**Note:** If you made changes on the Raspberry Pi, locally, you may need to run `git reset --hard origin/main` - doing so will **discard your local changes**, so ensure you've committed them from a seperate machine first.