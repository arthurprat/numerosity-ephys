from exptools2.core import PylinkEyetrackerSession, Trial
from psychopy import event
from stimuli import ResponseSlider, FixationLines
import yaml
import os.path as op
import numpy as np

import time

class EstimationSession(PylinkEyetrackerSession):
    def __init__(self, output_str, range, subject=None, output_dir=None, settings_file=None, run=None, eyetracker_on=False,
                 calibrate_eyetracker=False, sendPulses=False):

        super().__init__(output_str, output_dir=output_dir, settings_file=settings_file, eyetracker_on=eyetracker_on)

        # self.win.color = (-.25, -.25, -.25)

        self.show_eyetracker_calibration = calibrate_eyetracker
        self.sendPulses = sendPulses
        if self.sendPulses:
            self.eeglog_path = op.join(self.output_dir, "eeg.eeglog")
            self.eeglog = None

            import u3
            try:
                self.labjack = u3.U3() # Initialize LabJack
                print("Labjack connected")
            except:
                print("!!THE SYNC BOX IS NOT PLUGGED IN!! Connect the cable and restart the task.")
                ###exit()
                class FakeLabjack:
                    def setFIOState(self, channel, state):
                        if state == 1:
                            print(f'FakeLabjack: setFIOState called with channel {channel}, state {state}')
                    def close(self):
                        print('FakeLabjack: close.')
                self.labjack = FakeLabjack()
            self.labjack_timeDelay = np.random.uniform(0.8,1.2)
            self.labjack_startTime = None
        self.mouse = event.Mouse(visible=False)

        self.instructions = yaml.safe_load(open(op.join(op.dirname(__file__), 'instruction_texts.yml'), 'r'))

        self.settings['subject'] = subject
        self.settings['run'] = run
        self.settings['range_label'] = range
        self.settings['range'] = self.settings['ranges'].get(range)


        self.fixation_lines = FixationLines(self.win,
                                            self.settings['cloud'].get('aperture_radius'),
                                            color=(1, -1, -1),
                                            **self.settings['fixation_lines'])

        self._setup_response_slider()

    def _clock_to_unix_ms(self, psychopy_time=None):
        if psychopy_time is None:
            psychopy_time = self.clock.getTime()
        return round((self.clock._epochTimeAtLastReset + psychopy_time) * 1000)
    
    ######## PULSE ########
    ######## Inspired by 'Zaghloul Lab Synchronization Code' #######
    def labjack_pulse(self):
        if not self.sendPulses:
            return
        currentTime = self.clock.getTime()
        if currentTime > self.labjack_startTime+self.labjack_timeDelay:
            self.labjack.setFIOState(0,1)
            timestamp = self._clock_to_unix_ms(currentTime)
            toPrint = str(timestamp)+'\t1\t'+'CHANNEL_0_UP\n'
            self.eeglog.write(toPrint)
            time.sleep(0.01)
            self.labjack_startTime = currentTime
            self.labjack_timeDelay = np.random.uniform(0.8,1.2)
        else:
            self.labjack.setFIOState(0,0)
    
    def _setup_response_slider(self):

        position_slider = (0, 0)
        max_range = self.settings['slider'].get('max_range')[1] - self.settings['slider'].get('max_range')[0]
        prop_max_rating = (self.settings['range'][1] - self.settings['range'][0]) / max_range
        length_line = prop_max_rating * self.settings['slider'].get('max_length')

        self.response_slider = ResponseSlider(self.win,
                                         position_slider,
                                         length_line,
                                         self.settings['slider'].get('height'),
                                         self.settings['slider'].get('color'),
                                         self.settings['slider'].get('borderColor'),
                                         self.settings['range'],
                                         marker_position=None,
                                         markerColor=self.settings['slider'].get('markerColor'),
                                         borderWidth=self.settings['slider'].get('borderWidth'),
                                         text_height=self.settings['slider'].get('text_height'))

    def run(self):
        """ Runs experiment. """
        if self.eyetracker_on and self.show_eyetracker_calibration:
            self.calibrate_eyetracker()

        self.start_experiment()

        if self.sendPulses:
            self.eeglog = open(self.eeglog_path, "a")
            timestamp = self._clock_to_unix_ms(0.0)
            toPrint = str(timestamp)+'\t0\t'+'log starts\n'
            self.eeglog.write(toPrint)
            self.labjack_startTime = self.clock.getTime()
            print(self.labjack_startTime)

        if self.eyetracker_on:
            self.start_recording_eyetracker()
        for trial in self.trials:
            trial.run()
        
        if self.sendPulses:
            self.labjack.close()
            timestamp = self._clock_to_unix_ms()
            toPrint = str(timestamp)+'\t0\t'+'log stops\n'
            self.eeglog.write(toPrint)
            self.eeglog.close()

        self.close()

    def close(self):
        if self.closed:
            return None

        super().close()

        if self.global_log.empty:
            return None

        log_df = self.global_log.reset_index()
        log_df.insert(0, 'unix_timestamp', np.rint((self.clock._epochTimeAtLastReset + log_df['onset'].astype(float)) * 1000).astype('int64'))
        log_df['range'] = self.settings['range_label']
        if 'dot_positions' in log_df.columns:
            log_df['dot_positions'] = log_df['dot_positions'].where(log_df['event_type'] == 'stimulus', '')
        preferred_front_columns = [
            'unix_timestamp',
            'trial_nr',
            'onset',
            'range',
            'block_index',
            'event_type',
            'phase',
            'stimulus_format',
            'n',
            'response',
            'response_time',
            'start_marker_position',
            'total_reward',
            'onset_abs',
            'duration',
            'nr_frames',
            'jitter',
        ]
        preferred_end_columns = ['dot_positions']
        front_columns = [column for column in preferred_front_columns if column in log_df.columns]
        end_columns = [column for column in preferred_end_columns if column in log_df.columns]
        middle_columns = [
            column for column in log_df.columns
            if column not in front_columns and column not in end_columns
        ]
        log_df = log_df[front_columns + middle_columns + end_columns]
        self.global_log = log_df
        self.global_log.to_csv(op.join(self.output_dir, self.output_str + "_events.tsv"), sep="\t", index=False)
        self.global_log.to_csv(op.join(self.output_dir, "session.log"), sep="\t", index=False)
