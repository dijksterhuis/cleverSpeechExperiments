#!/usr/bin/env python3
import os

# attack def imports
from cleverspeech.graph.GraphConstructor import Constructor
from cleverspeech.graph import Constraints
from cleverspeech.graph.Losses import CTCLoss
from cleverspeech.graph import Optimisers
# from cleverspeech.graph import Procedures
from cleverspeech.graph import Outputs
from cleverspeech.data import Feeds

from cleverspeech.data.etl.batch_generators import get_standard_batch_generator
from cleverspeech.data.Results import SingleJsonDB, SingleFileWriter
from cleverspeech.eval import PerceptualStatsBatch
from cleverspeech.utils.RuntimeUtils import AttackSpawner
from cleverspeech.utils.Utils import log, args, lcomp

from SecEval import VictimAPI as DeepSpeech

from experiments.Perceptual.Synthesis.Synthesisers import Spectral, \
    DeterministicPlusNoise, Additive

import custom_defs


GPU_DEVICE = 0
MAX_PROCESSES = 1
SPAWN_DELAY = 30

AUDIOS_INDIR = "./samples/all/"
TARGETS_PATH = "./samples/cv-valid-test.csv"
OUTDIR = "./adv/regularised-synthesis/"
MAX_EXAMPLES = 100
MAX_TARGETS = 1000
MAX_AUDIO_LENGTH = 120000

TOKENS = " abcdefghijklmnopqrstuvwxyz'-"
BEAM_WIDTH = 500
LEARNING_RATE = 10
CONSTRAINT_UPDATE = "geom"
RESCALE = 0.95
DECODING_STEP = 100
NUMB_STEPS = DECODING_STEP ** 2
BATCH_SIZE = 10

ADDITIVE_N_OSC = 16
ADDITIVE_FRAME_LENGTH = 512
ADDITIVE_FRAME_STEP = 512
ADDITIVE_INITIAL_HZ = 1e-8

SPECTRAL_FRAME_STEP = 256
SPECTRAL_FRAME_LENGTH = 256
SPECTRAL_FFT_LENGTH = 256
SPECTRAL_CONSTANT = 64

SYNTHS = {
    "inharmonic": Additive.InHarmonic,
    "freqharmonic": Additive.FreqHarmonic,
    "fullharmonic": Additive.FullyHarmonic,
    "dn_inharmonic": DeterministicPlusNoise.InharmonicPlusPlain,
    "dn_freqharmonic": DeterministicPlusNoise.FreqHarmonicPlusPlain,
    "dn_fullharmonic": DeterministicPlusNoise.FullyHarmonicPlusPlain,
    "stft": Spectral.STFT,
}


def execute(settings, attack_fn, batch_gen):

    # set up the directory we'll use for results

    if not os.path.exists(settings["outdir"]):
        os.makedirs(settings["outdir"], exist_ok=True)

    file_writer = SingleFileWriter(settings["outdir"])

    # Write the current settings to "settings.json" file.

    settings_db = SingleJsonDB(settings["outdir"])
    settings_db.open("settings").put(settings)
    log("Wrote settings.")

    # Manage GPU memory and CPU processes usage.

    attack_spawner = AttackSpawner(
        gpu_device=settings["gpu_device"],
        max_processes=settings["max_spawns"],
        delay=settings["spawn_delay"],
        file_writer=file_writer,
    )

    with attack_spawner as spawner:
        for b_id, batch in batch_gen:
            log("Running for Batch Number: {}".format(b_id), wrap=True)
            spawner.spawn(settings, attack_fn, batch)

    # Run the stats function on all successful examples once all attacks
    # are completed.
    PerceptualStatsBatch.batch_generate_statistic_file(settings["outdir"])


def create_attack_graph(sess, batch, settings):

    synth_cls = SYNTHS[settings["synth_cls"]]
    synth = synth_cls(batch, **settings["synth"])

    feeds = Feeds.Attack(batch)
    attack = Constructor(sess, batch, feeds)

    attack.add_hard_constraint(
        Constraints.L2,
        r_constant=settings["rescale"],
        update_method=settings["constraint_update"],
    )

    attack.add_graph(
        custom_defs.SynthesisAttack,
        synth
    )

    attack.add_victim(
        DeepSpeech.Model,
        tokens=settings["tokens"],
        beam_width=settings["beam_width"]
    )

    attack.add_loss(CTCLoss)
    attack.create_loss_fn()

    attack.add_optimiser(
        Optimisers.AdamOptimiser,
        learning_rate=settings["learning_rate"]
    )

    attack.add_procedure(
        custom_defs.UpdateOnDecodingSynth,
        steps=settings["nsteps"],
        decode_step=settings["decode_step"]
    )

    attack.add_outputs(
        Outputs.Base,
        settings["outdir"],
    )

    attack.create_feeds()

    return attack


def inharmonic_run(master_settings):
    synth_cls = "inharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def freq_harmonic_run(master_settings):

    synth_cls = "freqharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def full_harmonic_run(master_settings):

    synth_cls = "fullharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def detnoise_inharmonic_run(master_settings):

    synth_cls = "dn_inharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def detnoise_freq_harmonic_run(master_settings):

    synth_cls = "dn_freqharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def detnoise_full_harmonic_run(master_settings):

    synth_cls = "dn_fullharmonic"

    for run in range(ADDITIVE_N_OSC, 1, -4):

        outdir = os.path.join(OUTDIR, synth_cls + "/")
        outdir = os.path.join(outdir, "osc_{}/".format(run))

        settings = {
            "synth_cls": synth_cls,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "n_osc": ADDITIVE_N_OSC,
                "initial_hz": 1e-8,
                "frame_length": 512,
                "frame_step": 512,
                "normalise": False,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run {}.".format(run))


def spectral_regularised_run(master_settings):
    """
    CTC Loss attack modified from the original Carlini & Wagner work.

    Using a hard constraint is better for security evaluations, so we ignore the
    L2 distance regularisation term in the optimisation goal.

    TODO: I could probably remove `Base.add_loss()` method...?

    :return: None
    """
    def create_attack_graph(sess, batch, settings):

        synth_cls = SYNTHS[settings["synth_cls"]]
        synth = synth_cls(batch, **settings["synth"])

        feeds = Feeds.Attack(batch)
        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            custom_defs.SynthesisAttack,
            synth
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        attack.add_loss(CTCLoss)
        attack.add_loss(custom_defs.SpectralLoss)
        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            custom_defs.UpdateOnDecodingSynth,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"]
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    def run_generator(x, n):
        for i in range(1, n+1):
            if i == 0:
                yield x
            else:
                yield x
                x *= 2

    runs = lcomp(run_generator(SPECTRAL_CONSTANT, 8))

    synth = "stft"

    for run in runs:

        outdir = os.path.join(OUTDIR, synth + "/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
            "synth_cls": synth,
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "synth": {
                "frame_step": run,
                "frame_length": run,
                "fft_length": run * 2,
            },
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)
        batch_gen = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_gen)

        log("Finished run.")  # {}.".format(run))


if __name__ == '__main__':

    log("", wrap=True)

    experiments = {
        "stft": spectral_regularised_run,
        "additive-inharmonic": inharmonic_run,
        "additive-freq_harmonic": freq_harmonic_run,
        "additive-full_harmonic": full_harmonic_run,
        "detnoise-inharmonic": detnoise_inharmonic_run,
        "detnoise-freq_harmonic": detnoise_freq_harmonic_run,
        "detnoise-full_harmonic": detnoise_full_harmonic_run,
    }

    args(experiments)



