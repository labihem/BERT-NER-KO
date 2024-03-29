#! usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Copyright 2018 The Google AI Language Team Authors.
BASED ON Google_BERT.
@Author:zhoukaiyin

Partially modified by ymkim for Korean NER on 20190304
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import os
from bert import modeling
from bert import optimization
from bert import tokenization
import tensorflow as tf
# from sklearn.metrics import f1_score, precision_score, recall_score
from tensorflow.python.ops import math_ops
import tf_metrics
import pickle
import time

flags = tf.flags

FLAGS = flags.FLAGS

flags.DEFINE_string(
    "data_dir", None,
    "The input datadir.",
)

flags.DEFINE_string(
    "bert_config_file", None,
    "The config json file corresponding to the pre-trained BERT model."
)

flags.DEFINE_string(
    "task_name", None, "The name of the task to train."
)

flags.DEFINE_string(
    "output_dir", None,
    "The output directory where the model checkpoints will be written."
)

## Other parameters
flags.DEFINE_string(
    "init_checkpoint", None,
    "Initial checkpoint (usually from a pre-trained BERT model)."
)

flags.DEFINE_bool(
    "do_lower_case", True,
    "Whether to lower case the input text."
)

flags.DEFINE_integer(
    "max_seq_length", 128,
    "The maximum total input sequence length after WordPiece tokenization."
)

flags.DEFINE_bool(
    "do_train", False,
    "Whether to run training."
)
flags.DEFINE_bool("use_tpu", False, "Whether to use TPU or GPU/CPU.")

flags.DEFINE_bool("do_eval", False, "Whether to run eval on the dev set.")

flags.DEFINE_bool("do_predict", False, "Whether to run the model in inference mode on the test set.")

flags.DEFINE_bool("do_demo", False, "Whether to run the model in demo.")  # revised by th

flags.DEFINE_string("input_file_train", None, "file which will be trained")  # revised by th

flags.DEFINE_string("input_file_eval", None, "file which will be evaluated")  # revised by th

flags.DEFINE_integer("train_batch_size", 32, "Total batch size for training.")

flags.DEFINE_integer("eval_batch_size", 8, "Total batch size for eval.")

flags.DEFINE_integer("predict_batch_size", 8, "Total batch size for predict.")

flags.DEFINE_float("learning_rate", 5e-5, "The initial learning rate for Adam.")

flags.DEFINE_float("num_train_epochs", 3.0, "Total number of training epochs to perform.")

flags.DEFINE_float(
    "warmup_proportion", 0.1,
    "Proportion of training to perform linear learning rate warmup for. "
    "E.g., 0.1 = 10% of training.")

flags.DEFINE_integer("save_checkpoints_steps", 1000,
                     "How often to save the model checkpoint.")

flags.DEFINE_integer("iterations_per_loop", 1000,
                     "How many steps to make in each estimator call.")

flags.DEFINE_integer("eval_interval", 100, "evaluation interval during training.")

flags.DEFINE_string("vocab_file", None,
                    "The vocabulary file that the BERT model was trained on.")
tf.flags.DEFINE_string("master", None, "[Optional] TensorFlow master URL.")
flags.DEFINE_integer(
    "num_tpu_cores", 8,
    "Only used if `use_tpu` is True. Total number of TPU cores to use.")


class InputExample(object):
    """A single training/test example for simple sequence classification."""

    def __init__(self, guid, text, charlabel=None, label=None):
        """Constructs a InputExample.

        Args:
          guid: Unique id for the example.
          text_a: string. The untokenized text of the first sequence. For single
            sequence tasks, only this sequence must be specified.
          label: (Optional) string. The label of the example. This should be
            specified for train and dev examples, but not for test examples.
        """
        self.guid = guid
        self.text = text
        self.charlabel = charlabel
        self.label = label


class InputFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids, label_ids, ):
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_ids = label_ids
        # self.label_mask = label_mask


class DataProcessor(object):
    """Base class for data converters for sequence classification data sets."""

    def get_train_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the train set."""
        raise NotImplementedError()

    def get_dev_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the dev set."""
        raise NotImplementedError()

    def get_labels(self):
        """Gets the list of labels for this data set."""
        raise NotImplementedError()

    @classmethod
    def _read_data(cls, input_file):
        """Reads a BIO data."""

        # Modified by ymkim
        #
        # data format:
        # each line has the following information.
        # [word charlabel label]
        #
        # ex)
        # -DOCSTART- -X- -X- O
        #
        # 지끈거리는 OOOOO O
        # 두통과 XXO B-ST
        # 구토증상이 XXOOO B-ST
        # 동반되는 OOOO O
        # 것으로 OOO O
        # 보아 OO O
        # 혈관성 XXX B-DS
        # 편두통의 XXXO I-DS
        # 가능성이 OOOO O
        # 있어보입니다 OOOOOO O
        # . O O
        #
        with open(input_file) as f:
            lines = []
            words = []
            labels = []
            charlabels = []  # pattern for the matching of each syllable to the label
            for line in f:
                contends = line.strip()
                word = line.strip().split(' ')[0]
                label = line.strip().split(' ')[-1]
                if word:
                    charlabel = (line.strip().split(' '))[1]
                else:
                    charlabel = ''
                if contends.startswith("-DOCSTART-"):
                    words.append('')
                    charlabels.append('')
                    continue
                if len(contends) == 0 and words[-1] == '.':
                    l = ' '.join([label for label in labels if len(label) > 0])
                    c = ' '.join([charlabel for charlabel in charlabels if len(charlabel) > 0])
                    w = ' '.join([word for word in words if len(word) > 0])
                    lines.append([l, c, w])
                    words = []
                    labels = []
                    charlabels = []
                    continue
                words.append(word)
                labels.append(label)
                charlabels.append(charlabel)

            return lines


class NerProcessor(DataProcessor):
    def get_train_examples(self, data_dir):
        return self._create_example(
            # self._read_data(os.path.join(data_dir, "train.txt")), "train"
            self._read_data(os.path.join(data_dir, FLAGS.input_file_train)), "train"
        )

    def get_dev_examples(self, data_dir):
        return self._create_example(
            self._read_data(os.path.join(data_dir, FLAGS.input_file_eval)), "dev"
        )

    def get_test_examples(self, data_dir):
        return self._create_example(
            self._read_data(os.path.join(data_dir, FLAGS.input_file_eval)), "test")

    def get_labels(self):
        # Modified by ymkim
        # There are six different labels + 1 outside + X + [CLS] + [SEP]

        # return ["B-MISC", "I-MISC", "O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC", "X","[CLS]","[SEP]"]
        return ["B-DS", "I-DS", "O", "B-ST", "I-ST", "B-BD", "I-BD", "X", "[CLS]", "[SEP]"]

    def _create_example(self, lines, set_type):
        examples = []
        for (i, line) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text = tokenization.convert_to_unicode(line[2])
            charlabel = tokenization.convert_to_unicode(line[1])
            label = tokenization.convert_to_unicode(line[0])
            examples.append(InputExample(guid=guid, text=text, charlabel=charlabel, label=label))
        return examples


def write_tokens(tokens, mode):
    if mode == "test":
        path = os.path.join(FLAGS.output_dir, "token_" + mode + ".txt")
        wf = open(path, 'a')
        for token in tokens:
            if token != "**NULL**":
                wf.write(token + '\n')
        wf.close()


def write_true_labels(labels, mode):
    # Created by ymkim

    if mode == "test":
        path = os.path.join(FLAGS.output_dir, "truelabel_" + mode + ".txt")
        wf = open(path, 'a')
        for label in labels:
            if label != "**NULL**":
                wf.write(label + '\n')
        wf.close()


def convert_single_example(ex_index, example, label_list, max_seq_length, tokenizer, mode):
    # Modified by ymkim

    label_map = {}
    for (i, label) in enumerate(label_list, 1):
        label_map[label] = i
    with open('./output/label2id.pkl', 'wb') as w:
        pickle.dump(label_map, w)
    textlist = example.text.split(' ')
    charlabellist = example.charlabel.split(' ')  # added variable to write real label
    labellist = example.label.split(' ')
    tokens = []
    labels = []
    for i, word in enumerate(textlist):
        token = tokenizer.tokenize(word)
        tokens.extend(token)
        label_1 = labellist[i]  # label of the line
        pattern = charlabellist[i]  # real label pattern for each syllable
        for m in range(len(token)):
            if m == 0:  # for the first token after the tokenization
                labels.append(label_1)
            elif label_1 != "O" and pattern[m] == "O":  # although word label is not "O", if the syllable's label is "O"
                labels.append("O")
            else:
                labels.append("X")

    # tokens = tokenizer.tokenize(example.text)
    if len(tokens) >= max_seq_length - 1:
        tokens = tokens[0:(max_seq_length - 2)]
        labels = labels[0:(max_seq_length - 2)]
    ntokens = []
    segment_ids = []
    label_ids = []
    label_original = []  # added by ymkim to write the true labels
    ntokens.append("[CLS]")
    segment_ids.append(0)
    # append("O") or append("[CLS]") not sure!
    label_ids.append(label_map["[CLS]"])
    label_original.append("[CLS]")
    for i, token in enumerate(tokens):
        ntokens.append(token)
        segment_ids.append(0)
        label_ids.append(label_map[labels[i]])
        label_original.append(labels[i])
    ntokens.append("[SEP]")
    segment_ids.append(0)
    # append("O") or append("[SEP]") not sure!
    label_ids.append(label_map["[SEP]"])
    label_original.append("[SEP]")
    input_ids = tokenizer.convert_tokens_to_ids(ntokens)
    input_mask = [1] * len(input_ids)
    # label_mask = [1] * len(input_ids)
    while len(input_ids) < max_seq_length:
        input_ids.append(0)
        input_mask.append(0)
        segment_ids.append(0)
        # we don't concerned about it!
        label_ids.append(0)
        ntokens.append("**NULL**")
        # label_mask.append(0)
    # print(len(input_ids))
    assert len(input_ids) == max_seq_length
    assert len(input_mask) == max_seq_length
    assert len(segment_ids) == max_seq_length
    assert len(label_ids) == max_seq_length
    # assert len(label_mask) == max_seq_length

    if ex_index < 5:
        tf.logging.info("*** Example ***")
        tf.logging.info("guid: %s" % (example.guid))
        tf.logging.info("tokens: %s" % " ".join(
            [tokenization.printable_text(x) for x in tokens]))
        tf.logging.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
        tf.logging.info("input_mask: %s" % " ".join([str(x) for x in input_mask]))
        tf.logging.info("segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
        tf.logging.info("label_ids: %s" % " ".join([str(x) for x in label_ids]))
        # tf.logging.info("label_mask: %s" % " ".join([str(x) for x in label_mask]))

    feature = InputFeatures(
        input_ids=input_ids,
        input_mask=input_mask,
        segment_ids=segment_ids,
        label_ids=label_ids,
        # label_mask = label_mask
    )
    write_tokens(ntokens, mode)
    write_true_labels(label_original, mode)  # added by ymkim
    return feature


def filed_based_convert_examples_to_features(
        examples, label_list, max_seq_length, tokenizer, output_file, mode=None
):
    writer = tf.python_io.TFRecordWriter(output_file)
    for (ex_index, example) in enumerate(examples):
        if ex_index % 5000 == 0:
            tf.logging.info("Writing example %d of %d" % (ex_index, len(examples)))
        feature = convert_single_example(ex_index, example, label_list, max_seq_length, tokenizer, mode)

        def create_int_feature(values):
            f = tf.train.Feature(int64_list=tf.train.Int64List(value=list(values)))
            return f

        features = collections.OrderedDict()
        features["input_ids"] = create_int_feature(feature.input_ids)
        features["input_mask"] = create_int_feature(feature.input_mask)
        features["segment_ids"] = create_int_feature(feature.segment_ids)
        features["label_ids"] = create_int_feature(feature.label_ids)
        # features["label_mask"] = create_int_feature(feature.label_mask)
        tf_example = tf.train.Example(features=tf.train.Features(feature=features))
        writer.write(tf_example.SerializeToString())


def file_based_input_fn_builder(input_file, seq_length, is_training, drop_remainder):
    name_to_features = {
        "input_ids": tf.FixedLenFeature([seq_length], tf.int64),
        "input_mask": tf.FixedLenFeature([seq_length], tf.int64),
        "segment_ids": tf.FixedLenFeature([seq_length], tf.int64),
        "label_ids": tf.FixedLenFeature([seq_length], tf.int64),
        # "label_ids":tf.VarLenFeature(tf.int64),
        # "label_mask": tf.FixedLenFeature([seq_length], tf.int64),
    }

    def _decode_record(record, name_to_features):
        example = tf.parse_single_example(record, name_to_features)
        for name in list(example.keys()):
            t = example[name]
            if t.dtype == tf.int64:
                t = tf.to_int32(t)
            example[name] = t
        return example

    def input_fn(params):
        batch_size = params["batch_size"]
        d = tf.data.TFRecordDataset(input_file)
        if is_training:
            d = d.repeat()
            d = d.shuffle(buffer_size=100)
        d = d.apply(tf.contrib.data.map_and_batch(
            lambda record: _decode_record(record, name_to_features),
            batch_size=batch_size,
            drop_remainder=drop_remainder
        ))
        return d

    return input_fn


def create_model(bert_config, is_training, input_ids, input_mask,
                 segment_ids, labels, num_labels, use_one_hot_embeddings):
    model = modeling.BertModel(
        config=bert_config,
        is_training=is_training,
        input_ids=input_ids,
        input_mask=input_mask,
        token_type_ids=segment_ids,
        use_one_hot_embeddings=use_one_hot_embeddings
    )

    output_layer = model.get_sequence_output()

    hidden_size = output_layer.shape[-1].value

    output_weight = tf.get_variable(
        "output_weights", [num_labels, hidden_size],
        initializer=tf.truncated_normal_initializer(stddev=0.02)
    )
    output_bias = tf.get_variable(
        "output_bias", [num_labels], initializer=tf.zeros_initializer()
    )
    with tf.variable_scope("loss"):
        if is_training:
            output_layer = tf.nn.dropout(output_layer, keep_prob=0.9)
        output_layer = tf.reshape(output_layer, [-1, hidden_size])
        logits = tf.matmul(output_layer, output_weight, transpose_b=True)
        logits = tf.nn.bias_add(logits, output_bias)
        logits = tf.reshape(logits, [-1, FLAGS.max_seq_length, 11])
        # mask = tf.cast(input_mask,tf.float32)
        # loss = tf.contrib.seq2seq.sequence_loss(logits,labels,mask)
        # return (loss, logits, predict)
        ##########################################################################
        log_probs = tf.nn.log_softmax(logits, axis=-1)
        one_hot_labels = tf.one_hot(labels, depth=num_labels, dtype=tf.float32)
        per_example_loss = -tf.reduce_sum(one_hot_labels * log_probs, axis=-1)
        loss = tf.reduce_sum(per_example_loss)
        probabilities = tf.nn.softmax(logits, axis=-1)
        predict = tf.argmax(probabilities, axis=-1)
        return (loss, per_example_loss, logits, predict)
        ##########################################################################


def model_fn_builder(bert_config, num_labels, init_checkpoint, learning_rate,
                     num_train_steps, num_warmup_steps, use_tpu,
                     use_one_hot_embeddings):
    def model_fn(features, labels, mode, params):
        tf.logging.info("*** Features ***")
        for name in sorted(features.keys()):
            tf.logging.info("  name = %s, shape = %s" % (name, features[name].shape))
        input_ids = features["input_ids"]
        input_mask = features["input_mask"]
        segment_ids = features["segment_ids"]
        label_ids = features["label_ids"]
        # label_mask = features["label_mask"]
        is_training = (mode == tf.estimator.ModeKeys.TRAIN)

        (total_loss, per_example_loss, logits, predicts) = create_model(
            bert_config, is_training, input_ids, input_mask, segment_ids, label_ids,
            num_labels, use_one_hot_embeddings)
        tvars = tf.trainable_variables()
        scaffold_fn = None
        if init_checkpoint:
            (assignment_map, initialized_variable_names) = modeling.get_assignment_map_from_checkpoint(tvars,
                                                                                                       init_checkpoint)
            tf.train.init_from_checkpoint(init_checkpoint, assignment_map)
            if use_tpu:
                def tpu_scaffold():
                    tf.train.init_from_checkpoint(init_checkpoint, assignment_map)
                    return tf.train.Scaffold()

                scaffold_fn = tpu_scaffold
            else:
                tf.train.init_from_checkpoint(init_checkpoint, assignment_map)
        tf.logging.info("**** Trainable Variables ****")

        for var in tvars:
            init_string = ""
            if var.name in initialized_variable_names:
                init_string = ", *INIT_FROM_CKPT*"
            tf.logging.info("  name = %s, shape = %s%s", var.name, var.shape,
                            init_string)
        output_spec = None
        if mode == tf.estimator.ModeKeys.TRAIN:
            train_op = optimization.create_optimizer(
                total_loss, learning_rate, num_train_steps, num_warmup_steps, use_tpu)
            output_spec = tf.contrib.tpu.TPUEstimatorSpec(
                mode=mode,
                loss=total_loss,
                train_op=train_op,
                scaffold_fn=scaffold_fn)
        elif mode == tf.estimator.ModeKeys.EVAL:

            def metric_fn(per_example_loss, label_ids, logits):
                # def metric_fn(label_ids, logits):
                # Modified by ymkim

                predictions = tf.argmax(logits, axis=-1, output_type=tf.int32)
                precision = tf_metrics.precision(label_ids, predictions, 11, [1, 2, 4, 5, 6, 7], average="micro")
                recall = tf_metrics.recall(label_ids, predictions, 11, [1, 2, 4, 5, 6, 7], average="micro")
                f = tf_metrics.f1(label_ids, predictions, 11, [1, 2, 4, 5, 6, 7], average="micro")
                #
                return {
                    "eval_precision": precision,
                    "eval_recall": recall,
                    "eval_f": f,
                    # "eval_loss": loss,
                }

            eval_metrics = (metric_fn, [per_example_loss, label_ids, logits])
            # eval_metrics = (metric_fn, [label_ids, logits])
            output_spec = tf.contrib.tpu.TPUEstimatorSpec(
                mode=mode,
                loss=total_loss,
                eval_metrics=eval_metrics,
                scaffold_fn=scaffold_fn)
        else:
            output_spec = tf.contrib.tpu.TPUEstimatorSpec(
                mode=mode, predictions=predicts, scaffold_fn=scaffold_fn
            )
        return output_spec

    return model_fn


def get_entity(tokens, labels):
    DS = get_DS_entity(tokens, labels)
    ST = get_ST_entity(tokens, labels)
    BD = get_BD_entity(tokens, labels)
    return DS, ST, BD


def get_DS_entity(tokens, labels):
    ch = ''
    DS = []
    seq = False
    for token, label in zip(tokens, labels):
        # print(token, label)
        if label not in ['B-DS', 'I-DS', 'X'] and seq:
            DS.append(ch)
            ch = ''
            seq = False
        if label == 'B-DS':
            if seq:
                DS.append(ch)
                ch = token
            else:
                ch += token
                seq = True
        if label == 'X' and seq:
            ch += token
        if label == 'I-DS' and seq:
            ch = ch + ' ' + token
    return DS


def get_ST_entity(tokens, labels):
    ch = ''
    ST = []
    seq = False
    for token, label in zip(tokens, labels):
        # print(token, label)
        if label not in ['B-ST', 'I-ST', 'X'] and seq:
            ST.append(ch)
            ch = ''
            seq = False
        if label == 'B-ST':
            if seq:
                ST.append(ch)
                ch = token
            else:
                ch += token
                seq = True
        if label == 'X' and seq:
            ch += token
        if label == 'I-ST' and seq:
            ch = ch + ' ' + token
    return ST


def get_BD_entity(tokens, labels):
    ch = ''
    BD = []
    seq = False
    for token, label in zip(tokens, labels):
        # print(token, label)
        if label not in ['B-BD', 'I-BD', 'X'] and seq:
            BD.append(ch)
            ch = ''
            seq = False
        if label == 'B-BD':
            if seq:
                BD.append(ch)
                ch = token
            else:
                ch += token
                seq = True
        if label == 'X' and seq:
            ch += token
        if label == 'I-BD' and seq:
            ch = ch + ' ' + token
    return BD


def create_serving_input_receiver_fn(max_seq_length):
    """ Builds a serving_inputer_receiver_fn
    Arguments
    ---------
    max_seq_length: int
        Specifies the sequence length
    Returns
    -------
    serving_input_receiver_fn()
    """

    def serving_input_receiver_fn():
        """ Creates an serving_input_receiver_fn for BERT"""
        unique_ids = tf.placeholder(tf.int32, [None], name="unique_ids")
        input_ids = tf.placeholder(tf.int32, [None, max_seq_length], name="input_ids")
        input_mask = tf.placeholder(tf.int32, [None, max_seq_length], name="input_mask")
        segment_ids = tf.placeholder(tf.int32, [None, max_seq_length], name="segment_ids")
        label_ids = tf.placeholder(tf.int32, [None], name="label_ids")
        return tf.estimator.export.build_raw_serving_input_receiver_fn(
            {
                "unique_ids": unique_ids,
                "input_ids": input_ids,
                "input_mask": input_mask,
                "segment_ids": segment_ids,
                "label_ids": label_ids,
            }
        )()

    return serving_input_receiver_fn


# It provides predictions of input data which users randomly enter by keyboard.
def demo(bert_config, label_list, tokenizer, run_config):
    init_checkpoint = "./output/model.ckpt-3518"  # model.ckpt-3518 was trained using diagnosis data
    model_fn = model_fn_builder(
        bert_config=bert_config,
        num_labels=len(label_list) + 1,
        init_checkpoint=init_checkpoint,
        learning_rate=FLAGS.learning_rate,
        num_train_steps=None,
        num_warmup_steps=None,
        use_tpu=FLAGS.use_tpu,
        use_one_hot_embeddings=FLAGS.use_tpu)

    estimator = tf.contrib.tpu.TPUEstimator(
        use_tpu=FLAGS.use_tpu,
        model_fn=model_fn,
        config=run_config,
        train_batch_size=FLAGS.train_batch_size,
        eval_batch_size=FLAGS.eval_batch_size,
        predict_batch_size=FLAGS.predict_batch_size)

    token_path = os.path.join(FLAGS.output_dir, "token_test.txt")
    truelabel_path = os.path.join(FLAGS.output_dir, "truelabel_test.txt")  # added by ymkim
    with open('./output/label2id.pkl', 'rb') as rf:
        label2id = pickle.load(rf)
        id2label = {value: key for key, value in label2id.items()}

    print('============= demo =============')
    while True:
        print('Please input your sentences:')
        demo_text = input()

        start = time.time()  # 시작 시간 저장

        if os.path.exists(token_path):
            os.remove(token_path)
        if os.path.exists(truelabel_path):
            os.remove(truelabel_path)

        len_t = len(demo_text.split(' '))
        # Below two variables will not be used to predict.
        # So It doesn't matter which character comes, If Its length matches 'demo_text.split()'.
        demo_label = 'O ' * len_t
        demo_charlabel = 'O ' * len_t

        # Create predict_examples using creator of InputExample that is defined in this file above
        # Arguments : guid, text, label, charlabel
        # guid : 'test-#'
        # text : the input sentences put by user
        # charlabel : It is already created above.
        # label : It is already created above.
        predict_examples = []
        predict_examples.append(InputExample(guid='test-0',
                                             text=demo_text,
                                             label=demo_label,
                                             charlabel=demo_charlabel))

        predict_file = os.path.join(FLAGS.output_dir, "predict.tf_record")
        filed_based_convert_examples_to_features(predict_examples, label_list,
                                                 FLAGS.max_seq_length, tokenizer,
                                                 predict_file, mode="test")

        tf.logging.info("***** Running prediction*****")
        tf.logging.info("  Num examples = %d", len(predict_examples))
        tf.logging.info("  Batch size = %d", FLAGS.predict_batch_size)
        if FLAGS.use_tpu:
            # Warning: According to tpu_estimator.py Prediction on TPU is an
            # experimental feature and hence not supported here
            raise ValueError("Prediction in TPU not supported")
        predict_drop_remainder = True if FLAGS.use_tpu else False
        predict_input_fn = file_based_input_fn_builder(
            input_file=predict_file,
            seq_length=FLAGS.max_seq_length,
            is_training=False,
            drop_remainder=predict_drop_remainder)

        result = estimator.predict(input_fn=predict_input_fn)
        output_predict_file = os.path.join(FLAGS.output_dir, "label_test.txt")
        with open(output_predict_file, 'w') as writer:
            for prediction in result:
                output_line = "\n".join(id2label[id] for id in prediction if id != 0) + "\n"
                writer.write(output_line)

        # load output data that is 'label_test.txt' and 'token_test.txt from output folder.
        f = open(token_path, 'r')
        lines = f.readlines()
        tokens = []
        for i in lines:
            tokens.append(i.strip().replace('#', ''))
        f.close()

        f = open(output_predict_file, 'r')
        lines = f.readlines()
        labels = []
        for i in lines:
            labels.append(i.strip())
        f.close()

        DS, ST, BD = get_entity(tokens, labels)
        print('\n\nYour sentences : ' + demo_text + '\n')
        print('DS: {}\nST: {}\nBD: {}'.format(DS, ST, BD))

        print("time :", time.time() - start)  # current time - start time = running time


def main(_):
    tf.logging.set_verbosity(tf.logging.INFO)
    processors = {
        "ner": NerProcessor
    }
    if not FLAGS.do_train and not FLAGS.do_eval:
        raise ValueError("At least one of `do_train` or `do_eval` must be True.")

    bert_config = modeling.BertConfig.from_json_file(FLAGS.bert_config_file)

    if FLAGS.max_seq_length > bert_config.max_position_embeddings:
        raise ValueError(
            "Cannot use sequence length %d because the BERT model "
            "was only trained up to sequence length %d" %
            (FLAGS.max_seq_length, bert_config.max_position_embeddings))

    task_name = FLAGS.task_name.lower()
    if task_name not in processors:
        raise ValueError("Task not found: %s" % (task_name))
    processor = processors[task_name]()

    label_list = processor.get_labels()

    tokenizer = tokenization.FullTokenizer(
        vocab_file=FLAGS.vocab_file, do_lower_case=FLAGS.do_lower_case)
    tpu_cluster_resolver = None
    if FLAGS.use_tpu and FLAGS.tpu_name:
        tpu_cluster_resolver = tf.contrib.cluster_resolver.TPUClusterResolver(
            FLAGS.tpu_name, zone=FLAGS.tpu_zone, project=FLAGS.gcp_project)

    is_per_host = tf.contrib.tpu.InputPipelineConfig.PER_HOST_V2

    run_config = tf.contrib.tpu.RunConfig(
        cluster=tpu_cluster_resolver,
        master=FLAGS.master,
        model_dir=FLAGS.output_dir,
        save_checkpoints_steps=FLAGS.save_checkpoints_steps,
        tpu_config=tf.contrib.tpu.TPUConfig(
            iterations_per_loop=FLAGS.iterations_per_loop,
            num_shards=FLAGS.num_tpu_cores,
            per_host_input_for_training=is_per_host))

    train_examples = None
    num_train_steps = None
    num_warmup_steps = None
    eval_steps = None

    if FLAGS.do_demo:
        demo(bert_config, label_list, tokenizer, run_config)

    if FLAGS.do_train:
        train_examples = processor.get_train_examples(FLAGS.data_dir)
        num_train_steps = int(
            len(train_examples) / FLAGS.train_batch_size * FLAGS.num_train_epochs)
        num_warmup_steps = int(num_train_steps * FLAGS.warmup_proportion)

    eval_examples = processor.get_dev_examples(FLAGS.data_dir)
    eval_file = os.path.join(FLAGS.output_dir, "eval.tf_record")
    filed_based_convert_examples_to_features(
        eval_examples, label_list, FLAGS.max_seq_length, tokenizer, eval_file)
    if FLAGS.use_tpu:
        eval_steps = int(len(eval_examples) / FLAGS.eval_batch_size)
    eval_drop_remainder = True if FLAGS.use_tpu else False
    eval_input_fn = file_based_input_fn_builder(
        input_file=eval_file,
        seq_length=FLAGS.max_seq_length,
        is_training=False,
        drop_remainder=eval_drop_remainder)

    model_fn = model_fn_builder(
        bert_config=bert_config,
        num_labels=len(label_list) + 1,
        init_checkpoint=FLAGS.init_checkpoint,
        learning_rate=FLAGS.learning_rate,
        num_train_steps=num_train_steps,
        num_warmup_steps=num_warmup_steps,
        use_tpu=FLAGS.use_tpu,
        use_one_hot_embeddings=FLAGS.use_tpu)

    estimator = tf.contrib.tpu.TPUEstimator(
        use_tpu=FLAGS.use_tpu,
        model_fn=model_fn,
        config=run_config,
        train_batch_size=FLAGS.train_batch_size,
        eval_batch_size=FLAGS.eval_batch_size,
        predict_batch_size=FLAGS.predict_batch_size)

    if FLAGS.do_train:
        print("train")
        train_file = os.path.join(FLAGS.output_dir, "train.tf_record")
        filed_based_convert_examples_to_features(
            train_examples, label_list, FLAGS.max_seq_length, tokenizer, train_file)
        tf.logging.info("***** Running training *****")
        tf.logging.info("  Num examples = %d", len(train_examples))
        tf.logging.info("  Batch size = %d", FLAGS.train_batch_size)
        tf.logging.info("  Num steps = %d", num_train_steps)
        train_input_fn = file_based_input_fn_builder(
            input_file=train_file,
            seq_length=FLAGS.max_seq_length,
            is_training=True,
            drop_remainder=True)

        train_spec = tf.estimator.TrainSpec(input_fn=train_input_fn, max_steps=num_train_steps)

        eval_spec = tf.estimator.EvalSpec(
            eval_input_fn,
            steps=None,
            start_delay_secs=0,  # start evaluating 0 seconds after beginning of training
            throttle_secs=60  # evaluate every 60 seconds
        )
        tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)  # excute evaluation when saved checkpoint for using tensorboard

        export_dir = os.path.join(FLAGS.output_dir, "export")
        tf.logging.info("  Export model")
        estimator.export_saved_model(export_dir, create_serving_input_receiver_fn(FLAGS.max_seq_length))  # export model

    if FLAGS.do_eval:
        tf.logging.info("***** Running evaluation *****")
        tf.logging.info("  Num examples = %d", len(eval_examples))
        tf.logging.info("  Batch size = %d", FLAGS.eval_batch_size)

        result = estimator.evaluate(input_fn=eval_input_fn, steps=eval_steps)
        output_eval_file = os.path.join(FLAGS.output_dir, "eval_results.txt")
        with open(output_eval_file, "w") as writer:
            tf.logging.info("***** Eval results *****")
            for key in sorted(result.keys()):
                tf.logging.info("  %s = %s", key, str(result[key]))
                writer.write("%s = %s\n" % (key, str(result[key])))

    if FLAGS.do_predict:
        token_path = os.path.join(FLAGS.output_dir, "token_test.txt")
        truelabel_path = os.path.join(FLAGS.output_dir, "truelabel_test.txt")  # added by ymkim
        with open('./output/label2id.pkl', 'rb') as rf:
            label2id = pickle.load(rf)
            id2label = {value: key for key, value in label2id.items()}
        if os.path.exists(token_path):
            os.remove(token_path)
        if os.path.exists(truelabel_path):
            os.remove(truelabel_path)
        predict_examples = processor.get_test_examples(FLAGS.data_dir)

        predict_file = os.path.join(FLAGS.output_dir, "predict.tf_record")
        filed_based_convert_examples_to_features(predict_examples, label_list,
                                                 FLAGS.max_seq_length, tokenizer,
                                                 predict_file, mode="test")

        tf.logging.info("***** Running prediction*****")
        tf.logging.info("  Num examples = %d", len(predict_examples))
        tf.logging.info("  Batch size = %d", FLAGS.predict_batch_size)
        if FLAGS.use_tpu:
            # Warning: According to tpu_estimator.py Prediction on TPU is an
            # experimental feature and hence not supported here
            raise ValueError("Prediction in TPU not supported")
        predict_drop_remainder = True if FLAGS.use_tpu else False
        predict_input_fn = file_based_input_fn_builder(
            input_file=predict_file,
            seq_length=FLAGS.max_seq_length,
            is_training=False,
            drop_remainder=predict_drop_remainder)

        result = estimator.predict(input_fn=predict_input_fn)
        output_predict_file = os.path.join(FLAGS.output_dir, "label_test.txt")
        with open(output_predict_file, 'w') as writer:
            for prediction in result:
                output_line = "\n".join(id2label[id] for id in prediction if id != 0) + "\n"
                writer.write(output_line)


if __name__ == "__main__":
    flags.mark_flag_as_required("data_dir")
    flags.mark_flag_as_required("task_name")
    flags.mark_flag_as_required("vocab_file")
    flags.mark_flag_as_required("bert_config_file")
    flags.mark_flag_as_required("output_dir")
    tf.app.run()
