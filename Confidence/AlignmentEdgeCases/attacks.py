#!/usr/bin/env python3
import os

from cleverspeech.graph.GraphConstructor import Constructor
from cleverspeech.graph import Constraints
from cleverspeech.graph import Graphs
from cleverspeech.graph import Losses
from cleverspeech.graph import Optimisers
from cleverspeech.graph import Procedures
from cleverspeech.graph import Outputs
from cleverspeech.data import Feeds

from cleverspeech.data.etl.batch_generators import get_standard_batch_generator
from cleverspeech.data.etl.batch_generators import get_sparse_batch_generator
from cleverspeech.data.etl.batch_generators import get_dense_batch_factory
from cleverspeech.data.Results import SingleJsonDB, SingleFileWriter
from cleverspeech.eval import PerceptualStatsBatch
from cleverspeech.utils.RuntimeUtils import AttackSpawner
from cleverspeech.utils.Utils import log, args

# victim model
from SecEval import VictimAPI as DeepSpeech

# local attack classes
import custom_defs


GPU_DEVICE = 0
MAX_PROCESSES = 3
SPAWN_DELAY = 30

TOKENS = " abcdefghijklmnopqrstuvwxyz'-"
BEAM_WIDTH = 500

AUDIOS_INDIR = "./samples/all/"
TARGETS_PATH = "./samples/cv-valid-test.csv"
OUTDIR = "./adv/ctc-alignments/"

# targets search parameters
MAX_EXAMPLES = 100
MAX_TARGETS = 1000
MAX_AUDIO_LENGTH = 120000

RESCALE = 0.95
CONSTRAINT_UPDATE = "geom"
LEARNING_RATE = 10
NUMB_STEPS = 20000
DECODING_STEP = 10
BATCH_SIZE = 10

# extreme run settings
LOSS_UPDATE_THRESHOLD = 10.0
LOSS_UPDATE_NUMB_STEPS = 50000

N_RUNS = 1


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


def ctc_dense_alignment_run(master_settings):
    def create_attack_graph(sess, batch, settings):

        feeds = Feeds.Attack(batch)

        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            Graphs.SimpleAttack
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        attack.add_loss(custom_defs.RepeatsCTCLoss)

        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            Procedures.UpdateOnDecoding,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"]
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    for run in range(0, N_RUNS):

        outdir = os.path.join(OUTDIR, "dense/")
        outdir = os.path.join(outdir, "rctc/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
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
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)

        batch_factory = get_dense_batch_factory(settings)

        execute(settings, create_attack_graph, batch_factory)

        log("Finished run {}.".format(run))


def ctc_dense_extreme_alignment_run(master_settings):
    """
    As above, expect only update bounds when loss is below some threshold.
    """
    def create_attack_graph(sess, batch, settings):
        feeds = Feeds.Attack(batch)

        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            Graphs.SimpleAttack
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        attack.add_loss(custom_defs.RepeatsCTCLoss)

        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            Procedures.UpdateOnLoss,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"],
            loss_lower_bound=settings["loss_threshold"],
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    for run in range(0, N_RUNS):

        outdir = os.path.join(OUTDIR, "dense/")
        outdir = os.path.join(outdir, "extreme-rctc/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": LOSS_UPDATE_NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
            "loss_threshold": LOSS_UPDATE_THRESHOLD,
        }

        settings.update(master_settings)

        batch_factory = get_dense_batch_factory(settings)

        execute(settings, create_attack_graph, batch_factory)

        log("Finished run {}.".format(run))


def ctc_sparse_alignment_run(master_settings):
    def create_attack_graph(sess, batch, settings):

        feeds = Feeds.Attack(batch)

        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            Graphs.SimpleAttack
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        attack.add_loss(
            custom_defs.RepeatsCTCLoss,
        )

        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            Procedures.UpdateOnDecoding,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"],
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    for run in range(0, N_RUNS):

        outdir = os.path.join(OUTDIR, "sparse/")
        outdir = os.path.join(outdir, "rctc/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
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
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)

        batch_factory = get_sparse_batch_generator(settings)

        execute(settings, create_attack_graph, batch_factory)

        log("Finished run {}.".format(run))


def ctc_anti_sparse_alignment_run(master_settings):
    def create_attack_graph(sess, batch, settings):

        feeds = Feeds.Attack(batch)

        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            Graphs.SimpleAttack
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        alignment = Constructor(attack.sess, batch, feeds)
        alignment.add_graph(custom_defs.CTCSearchGraph, attack)
        alignment.add_loss(custom_defs.AlignmentLoss)
        alignment.create_loss_fn()
        alignment.add_optimiser(custom_defs.CTCAlignmentOptimiser)

        attack.add_loss(
            custom_defs.AntiCTC,
            alignment=alignment.graph.target_alignments,
        )
        attack.add_loss(
            custom_defs.RepeatsCTCLoss,
            alignment=alignment.graph.target_alignments,
        )

        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            custom_defs.CTCAlignmentsUpdateOnDecode,
            alignment_graph=alignment,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"],
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    for run in range(0, N_RUNS):

        outdir = os.path.join(OUTDIR, "sparse/")
        outdir = os.path.join(outdir, "rctc-anti/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
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
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
        }

        settings.update(master_settings)

        batch_factory = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_factory)

        log("Finished run {}.".format(run))


def ctc_sparse_extreme_alignment_run(master_settings):
    """
    As above, but this time we define `success` when the current loss is below a
    specified threshold.
    """
    def create_attack_graph(sess, batch, settings):

        feeds = Feeds.Attack(batch)

        attack = Constructor(sess, batch, feeds)

        attack.add_hard_constraint(
            Constraints.L2,
            r_constant=settings["rescale"],
            update_method=settings["constraint_update"],
        )

        attack.add_graph(
            Graphs.SimpleAttack
        )

        attack.add_victim(
            DeepSpeech.Model,
            tokens=settings["tokens"],
            beam_width=settings["beam_width"]
        )

        alignment = Constructor(attack.sess, batch, feeds)
        alignment.add_graph(custom_defs.CTCSearchGraph, attack)
        alignment.add_loss(custom_defs.AlignmentLoss)
        alignment.create_loss_fn()
        alignment.add_optimiser(custom_defs.CTCAlignmentOptimiser)

        attack.add_loss(
            custom_defs.RepeatsCTCLoss,
            alignment=alignment.graph.target_alignments,
        )

        attack.create_loss_fn()

        attack.add_optimiser(
            Optimisers.AdamOptimiser,
            learning_rate=settings["learning_rate"]
        )

        attack.add_procedure(
            custom_defs.CTCAlignmentsUpdateOnLoss,
            alignment_graph=alignment,
            steps=settings["nsteps"],
            decode_step=settings["decode_step"],
            loss_lower_bound=settings["loss_threshold"],
        )

        attack.add_outputs(
            Outputs.Base,
            settings["outdir"],
        )

        attack.create_feeds()

        return attack

    for run in range(0, N_RUNS):

        outdir = os.path.join(OUTDIR, "sparse/")
        outdir = os.path.join(outdir, "extreme-rctc/")
        outdir = os.path.join(outdir, "run_{}/".format(run))

        settings = {
            "audio_indir": AUDIOS_INDIR,
            "targets_path": TARGETS_PATH,
            "outdir": outdir,
            "batch_size": BATCH_SIZE,
            "tokens": TOKENS,
            "nsteps": LOSS_UPDATE_NUMB_STEPS,
            "decode_step": DECODING_STEP,
            "beam_width": BEAM_WIDTH,
            "constraint_update": CONSTRAINT_UPDATE,
            "rescale": RESCALE,
            "learning_rate": LEARNING_RATE,
            "gpu_device": GPU_DEVICE,
            "max_spawns": MAX_PROCESSES,
            "spawn_delay": SPAWN_DELAY,
            "max_examples": MAX_EXAMPLES,
            "max_targets": MAX_TARGETS,
            "max_audio_length": MAX_AUDIO_LENGTH,
            "loss_threshold": 1.0,
        }

        settings.update(master_settings)

        batch_factory = get_standard_batch_generator(settings)

        execute(settings, create_attack_graph, batch_factory)

        log("Finished run {}.".format(run))


if __name__ == '__main__':

    experiments = {
        "dense": ctc_dense_alignment_run,
        "sparse": ctc_sparse_alignment_run,
        "sparse-anti": ctc_anti_sparse_alignment_run,
        "dense-extreme": ctc_dense_extreme_alignment_run,
        "sparse-extreme": ctc_sparse_extreme_alignment_run,
    }

    args(experiments)
