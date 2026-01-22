# work in progress


1. Clone this repo

```
git clone https://github.com/arthurprat/numerosity-ephys.git
```

2. Create a virtual environment

Go to the repo :

```
cd numerosity-ephys
```

and run: (this creates a virtual environment named "env")

```
python -m venv env
```

3. Activate the virtual environment

```
. ./env/bin/activate
```

4. Install psychopy, exptools2, and LabJackPython

```
pip install psychopy LabJackPython
pip install git+https://github.com/Gilles86/exptools2/
```

5. Run an experiment

Go to the experiment repo:

```
cd experiment
```

<!-- Run the experiment for subject 01, session 1, with the narrow range, outside the scanner:

```
python run_noscanner_onerange.py 01 1 narrow
```

It might take a minute to start, the first time you run it.

A note about __important settings__:
- The number of trials in each of the three parts ('examples', with-feedback, without-feedback) is set in the settings yml file in `settings/`
(look for `example: n_examples`, `feedback: n_examples`, `task: n_trials`).
- The sizes of elements on screen (including slider size) depend on the specified screen width and distance of viewer. You can specify those in `monitor: width` and `monitor: distance`. -->

