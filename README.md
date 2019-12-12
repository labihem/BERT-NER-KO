# BERT-NER-KO
BERT for Korean NER

This is an implementation of Korean NER using BERT.
The code is a modified version of BERT-NER (https://github.com/kyzhouhzau/BERT-NER).
A new corpus for medical diagnosis information extraction has been used as the default data.

Usage:

1. Create a directory "BERT".

2. Go the the directory.
```
cd BERT
```

3. Clone the repository "bert".
```
git clone https://github.com/google-research/bert.git
```

4. Download the files and folder of this project to the directory "BERT".

5. Create a directory "pretrained" in the directory "bert".

6. Download and unzip the pretrained model, "BERT-Base, Multilingual Cased" https://storage.googleapis.com/bert_models/2018_11_23/multi_cased_L-12_H-768_A-12.zip in the directory "pretrained"

7. Create a directory "output".
The structure is as follows:
```
BERT
|____ bert
|____ data
      |____ diagnosis   
|____ BERT_NER_DS.py
|____ tf_metrics.py
|____ output
```

7. Run BERT_NER_DS.py

```
python3 BERT_NER_DS.py  \
  --task_name="NER"  \
  --do_lower_case=False  \
  --do_train=True   \
  --do_eval=True   \
  --do_predict=True  \
  --do_demo=False  \
  --data_dir=./data/diagnosis   \
  --input_file_train=train_diagnosis_shuffle1.txt   \
  --input_file_eval=eval_diagnosis_shuffle1.txt  \
  --vocab_file=./bert/pretrained/multi_cased_L-12_H-768_A-12/vocab.txt  \
  --bert_config_file=./bert/pretrained/multi_cased_L-12_H-768_A-12/bert_config.json  \
  --init_checkpoint=./bert/pretrained/multi_cased_L-12_H-768_A-12/bert_model.ckpt   \
  --max_seq_length=128   \
  --train_batch_size=32   \
  --learning_rate=2e-5   \
  --num_train_epochs=16.0   \
  --output_dir=./output
```
