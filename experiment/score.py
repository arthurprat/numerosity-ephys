import glob
import os.path as op
import argparse
import pandas as pd
import re
from pathlib import Path
from session import EstimationSession
from instruction import InstructionTrial
from utils import get_output_dir_str, get_settings
from exptools2.core import PylinkEyetrackerSession, Trial


def get_score_rows(log_df, feedback_phase=None):
    score_rows = log_df.set_index(['trial_nr', 'event_type']).xs('feedback', level='event_type').astype({'n': float, 'response': float})
    if feedback_phase is not None:
        score_rows = score_rows[score_rows['phase'] == feedback_phase]
    return score_rows


def get_subject_stats(subject, session, log_dir, max_reward=.1, reward_slope=.025, no_response_penalty=0.1):
    # Previous layout expected one subfolder per task/run:
    # feedback_log_files = glob.glob(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'task-feedback_run-*', 'session_events.tsv'))
    # estimation_log_files = glob.glob(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'task-estimation_task_run-*', 'session_events.tsv'))
    # print(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'task-feedback_run-*', 'session_events.tsv'))
    feedback_log_files = glob.glob(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'session_events.tsv'))
    estimation_log_files = glob.glob(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'session_events.tsv'))
    print(op.join(log_dir, f'sub-{subject}', f'ses-{session}', 'session_events.tsv'))

    # reg = re.compile(r'task-(?P<task>[a-zA-Z_]+)_run-(?P<run>[0-9]+)')
    reg = None

    stats = {}

    feedback_df = []
    for fn in feedback_log_files:
        run = reg.match(Path(fn).parent.name).group('run') if reg is not None else '1'
        d = pd.read_csv(fn, sep='\t')
        d['run'] = run
        feedback_df.append(d)

    feedback_df = pd.concat(feedback_df).set_index(['run', 'trial_nr', 'event_type']).xs('feedback', level='event_type').astype({'n':float, 'response':float})
    feedback_error = feedback_df['n'] - feedback_df['response']

    stats['mean_error_feedback'] = feedback_error.mean()
    stats['mean_abs_error_feedback'] = feedback_error.abs().mean()
    stats['mean_squared_error_feedback'] = feedback_error.pow(2).mean()
    stats['n_no_responses_feedback'] = feedback_error.isnull().sum()
    stats['total_reward_feedback'] = stats['n_no_responses_feedback'] *  no_response_penalty
    feedback_error = feedback_error[~feedback_error.isnull()]
    stats['total_reward_feedback'] += (max_reward - feedback_error.pow(2) * reward_slope).sum()
    stats['total_n_feedback_trials'] = len(feedback_error)

    estimation_df = []

    for fn in estimation_log_files:
        run = reg.match(Path(fn).parent.name).group('run') if reg is not None else '1'
        d = pd.read_csv(fn, sep='\t')
        d['run'] = run
        estimation_df.append(d)

    estimation_df = pd.concat(estimation_df).set_index(['run', 'trial_nr', 'event_type']).xs('feedback', level='event_type').astype({'n':float, 'response':float})
    estimation_error = estimation_df['n'] - estimation_df['response']

    stats['mean_error_estimation'] = estimation_error.mean()
    stats['mean_abs_error_estimation'] = estimation_error.abs().mean()
    stats['mean_squared_error_estimation'] = estimation_error.pow(2).mean()
    stats['n_no_responses_estimation'] = estimation_error.isnull().sum()
    stats['total_reward_estimation'] = stats['n_no_responses_estimation'] *  no_response_penalty
    estimation_error = estimation_error[~estimation_error.isnull()]
    stats['total_reward_estimation'] += (max_reward - estimation_error.pow(2) * reward_slope).sum()
    stats['total_n_estimation_trials'] = len(estimation_error)

    return stats

    
class ScoreSession(EstimationSession):

    def create_trials(self, session):

        no_response_penalty = self.settings['score']['no_response_penalty']
        max_reward = self.settings['score']['max_reward']
        reward_slope = self.settings['score']['reward_slope']

        log_dir = op.join(op.dirname(__file__), 'data')
        stats = get_subject_stats(self.settings['subject'], session, log_dir, max_reward, reward_slope, no_response_penalty)

        txt1 = self.instructions['score_feedback_summary'].format(
            total_n_feedback_trials=stats['total_n_feedback_trials'],
            n_no_responses_feedback=stats['n_no_responses_feedback'],
            lost_points_feedback=stats['n_no_responses_feedback'] * no_response_penalty,
            mean_error_feedback=stats['mean_error_feedback'],
            mean_abs_error_feedback=stats['mean_abs_error_feedback'],
            total_reward_feedback=stats['total_reward_feedback'],
        )

        txt2 = self.instructions['score_estimation_summary'].format(
            total_n_estimation_trials=stats['total_n_estimation_trials'],
            n_no_responses_estimation=stats['n_no_responses_estimation'],
            lost_points_estimation=stats['n_no_responses_estimation'] * no_response_penalty,
            mean_error_estimation=stats['mean_error_estimation'],
            mean_abs_error_estimation=stats['mean_abs_error_estimation'],
            total_reward_estimation=stats['total_reward_estimation'],
        )
        
        txt3 = self.instructions['score_total_summary'].format(
            total_points=stats['total_reward_feedback'] + stats['total_reward_estimation']
        )

        self.trials = [InstructionTrial(self, 0, txt1), InstructionTrial(self, 0, txt2), InstructionTrial(self, 0, txt3)]

class ScoreTrial(InstructionTrial):
    """ Simple trial with only fixation cross.  """

    def __init__(self, session, trial_nr=0, phase_durations=None, show_reward=True, feedback_phase=None,
                 block_index=None, total_blocks=None, bottom_txt='', **kwargs):

        #txt = '''Please lie still for a few moments.'''

        if phase_durations is None:
            phase_durations = [0.5, 5*60]

        self.log = session.global_log
        self.show_reward = show_reward
        self.feedback_phase = feedback_phase
        self.block_index = block_index
        self.total_blocks = total_blocks

        super().__init__(session=session, trial_nr=trial_nr, phase_durations=phase_durations, txt='',
                         bottom_txt=bottom_txt,
                         phase_names=['get_score', 'score'],
                         **kwargs)

    def draw(self):

        if self.session.sendPulses:
            self.session.labjack_pulse()

        if self.phase == 0:
            self.get_score()
            self.stop_phase()

        super().draw()

    def get_score(self):
        self.log = self.session.global_log.copy()
        self.log = get_score_rows(self.log, feedback_phase=self.feedback_phase)

        if self.log.empty:
            if self.block_index is not None and self.total_blocks is not None:
                self.text.text = self.session.instructions['score_block_summary_empty'].format(
                    current_block=self.block_index,
                    total_blocks=self.total_blocks,
                )
            else:
                self.text.text = self.session.instructions['score_final_summary'].format(
                    mean_abs_error=0.0,
                    total_reward=0.0,
                )
            return

        self.error = self.log['n'] - self.log['response']
        self.mean_error = self.error.mean()
        self.mean_abs_error = self.error.abs().mean()

        max_reward = self.session.settings['score']['max_reward']
        reward_slope = self.session.settings['score']['reward_slope']
        self.total_reward = (max_reward - self.error.pow(2) * reward_slope).sum()
        self.parameters['total_reward'] = self.total_reward

        if self.block_index is not None and self.total_blocks is not None:
            self.text.text = self.session.instructions['score_block_summary'].format(
                current_block=self.block_index,
                total_blocks=self.total_blocks,
                total_reward=self.total_reward,
                mean_abs_error=self.mean_abs_error,
            )
        else:
            self.text.text = self.session.instructions['score_final_summary'].format(
                mean_abs_error=self.mean_abs_error,
                total_reward=self.total_reward,
            )

        

def main(subject, session, settings):

    output_dir, output_str = get_output_dir_str(subject, session, 'score', 0)

    settings_fn, use_eyetracker = get_settings(settings)

    session_ = ScoreSession(output_str=output_str,
                            range='narrow',
                           subject=subject, output_dir=output_dir, eyetracker_on=use_eyetracker,
                           settings_file=settings_fn)

    session_.create_trials(session)

    session_.run()

if __name__ == "__main__":

    argparser = argparse.ArgumentParser()
    argparser.add_argument('subject', type=str, help='Subject nr')
    argparser.add_argument('session', type=str, help='Session')
    argparser.add_argument('--settings', type=str, help='Settings label', default='default')
    args = argparser.parse_args()

    main(args.subject, args.session, args.settings)
