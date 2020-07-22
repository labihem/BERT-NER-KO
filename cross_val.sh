for i in {1..5}
do
   echo "Cross validation $i"
   rm -rf ./output/*
   python3 BERT_NER_DS.py  --task_name="NER"   --do_lower_case=False  --do_train=True  --do_eval=False  --do_predict=True  --do_demo=False  --data_dir=./data/diagnosis  --input_file_train=train_diagnosis_shuffle$i.txt  --input_file_eval=eval_diagnosis_shuffle$i.txt --vocab_file=./bert/pretrained/multi_cased_L-12_H-768_A-12/vocab.txt --bert_config_file=./bert/pretrained/multi_cased_L-12_H-768_A-12/bert_config.json  --init_checkpoint=./bert/pretrained/multi_cased_L-12_H-768_A-12/bert_model.ckpt    --max_seq_length=128  --train_batch_size=32  --learning_rate=2e-5  --num_train_epochs=16.0  --save_checkpoints_steps=5000  --output_dir=./output

   mv ./output/truelabel_test.txt ./result_CV/truelabel_test_$i.txt
   mv ./output/label_test.txt ./result_CV/label_test_$i.txt

done
