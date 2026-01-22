import argparse
from session import EstimationSession
from examples import ExampleTrial
from feedback import FeedbackTrial
from score import ScoreTrial, get_subject_stats
from task import TaskTrial
from utils import get_output_dir_str, get_settings, OutroTrial, DummyWaiterTrial
import os.path as op
from score import ScoreSession
import datetime
import numpy as np
from instruction import InstructionTrial


class OneRangeSession(EstimationSession):

    def create_trials(self, session):
        """Create trials."""

        self.trials = []

        ###### EXAMPLES ######
        instruction_trial2 = InstructionTrial(self, 0, self.instructions['intro_block'].format(range_low=self.settings['range'][0], range_high=self.settings['range'][1]))
        n_examples = self.settings['examples'].get('n_examples')
        instruction_trial3 = InstructionTrial(self, 0, self.instructions['intro_part1'].format(n_examples=n_examples))

        self.trials += [instruction_trial2, instruction_trial3]

        ns = np.random.randint(self.settings['range'][0], self.settings['range'][1] + 1, n_examples)

        ns[0] = self.settings['range'][0]
        ns[1] = self.settings['range'][1]

        self.trials += [ExampleTrial(self, i+1, n=n) for i, n in enumerate(ns)]

        ######## FEEDBACK ######

        instruction_trial1 = InstructionTrial(self, 0, self.instructions['intro_part2'])
        instruction_trial2 = InstructionTrial(self, 0, self.instructions['intro_block'].format(range_low=self.settings['range'][0],
                                                                                            range_high=self.settings['range'][1]))
                                                                                            
        self.trials += [instruction_trial1, instruction_trial2]
        n_examples = self.settings['feedback'].get('n_examples')
        ns = np.random.randint(self.settings['range'][0], self.settings['range'][1] + 1, n_examples)

        self.trials += [FeedbackTrial(self, i+1, n=n) for i, n in enumerate(ns)]

        if not self.settings.get('skip_outro', False):
            self.trials.append(OutroTrial(session=self))

        # self.trials.append(ScoreTrial(self, 0))

        ######## TASK ######

        instruction_trial1 = InstructionTrial(self, 0, self.instructions['intro_part3'].format(run=self.settings['run']))
        instruction_trial2 = InstructionTrial(self, 0, self.instructions['intro_block'].format(range_low=self.settings['range'][0],
                                                                                            range_high=self.settings['range'][1]))

        dummy_trial = DummyWaiterTrial(self, 0, n_triggers=self.settings['mri']['n_dummy_scans'])
        
        self.trials += [instruction_trial1, instruction_trial2, dummy_trial]
        # if not include_instructions:
        #     self.trials = self.trials[1:]

        n_trials = self.settings['task'].get('n_trials')
        range = self.settings['range']
        ns = np.random.randint(range[0], range[1] + 1, n_trials)

        no_isi_no_jitter = self.settings.get('no_isi_no_jitter', False)
        if no_isi_no_jitter:
            self.trials += [TaskTrial(self, i+1, jitter=0, n=n, stimulus_series=self.settings['cloud']['stimulus_series']) for i,n in enumerate(ns)]
        else:
            possible_isis = self.settings['durations'].get('isi')
            isis = possible_isis * int(np.ceil(n_trials / len(possible_isis)))
            isis = isis[:n_trials]
            np.random.shuffle(isis)

            self.trials += [TaskTrial(self, i+1, jitter=jitter, n=n, stimulus_series=self.settings['cloud']['stimulus_series']) for i, (n, jitter) in enumerate(zip(ns, isis))]

        if not self.settings.get('skip_outro', False):
            self.trials.append(OutroTrial(session=self))

        self.trials.append(ScoreTrial(self, 0, keys=['q',]))



def main(subject, session, range, settings, run_examples=True, run_feedback=True):

    settings_fn, use_eyetracker = get_settings(settings)

    _RUN = 1

    output_dir, output_str = get_output_dir_str(subject, session, 'estimation_task', run=_RUN)
    print(output_dir, output_str)

    one_range_session = OneRangeSession(output_str=output_str, subject=subject,
                         output_dir=output_dir, settings_file=settings_fn, 
                         run=_RUN, range=range, eyetracker_on=use_eyetracker)
    
    one_range_session.create_trials(session=session)

    one_range_session.run()

    #print(one_range_session.global_log)
    one_range_session.global_log.to_csv(op.join(output_dir, f'{output_str}_global_log.csv'))

    print(one_range_session.trials[-1].text.text)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('subject', type=str, help='Subject nr')
    argparser.add_argument('session', type=str, help='Session')
    #argparser.add_argument('start_run', type=int, help='Start run #')
    argparser.add_argument('range', choices=['narrow', 'wide'], help='Range (narrow or wide)')
    argparser.add_argument('--settings', type=str, help='Settings label', default='noscanner')
    #argparser.add_argument('--n_runs_per_range', type=int, default=4, help='Number of runs per range') 
    argparser.add_argument('--no_examples', action='store_false', help='Do not run examples block')
    argparser.add_argument('--no_feedback', action='store_false', help='Do not run feedback block')
    args = argparser.parse_args()
    main(subject=args.subject, session=args.session, range=args.range, settings=args.settings, 
         run_examples=args.no_examples, run_feedback=args.no_feedback)