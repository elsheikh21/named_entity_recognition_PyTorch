import os
import logging
from os import getcwd
from os.path import join

from torch.nn import CrossEntropyLoss
from torch.nn.utils.rnn import pad_sequence
from torch.optim import Adam
from torch.utils.data import DataLoader

from callbacks import WriterTensorboardX
from data_loader import TSVDatasetParser
from evaluator import Evaluator
from models import HyperParameters, BaselineModel, CRF_Model
from training import Trainer, CRF_Trainer
from utilities import configure_workspace, load_pretrained_embeddings, torch_summarize, load_pickle

"""
Was implemented in order to test and run CRF Models
"""


def pad_per_batch(batch):
    data_x, data_y = [], []
    for item in batch:
        data_x.append(item.get('inputs'))
        data_y.append(item.get('outputs'))
    data_x = pad_sequence(data_x, batch_first=True, padding_value=0)
    data_y = pad_sequence(data_y, batch_first=True, padding_value=0)
    return data_x.to('cuda'), data_y.to('cuda')


def prepare_data(crf_model, word2idxpath=None):
    DATA_PATH = join(getcwd(), 'data')

    print("==========Training Dataset==========")
    file_path_ = join(DATA_PATH, 'train.tsv')
    training_set = TSVDatasetParser(file_path_, verbose=False, max_len=80, is_crf=crf_model, word2idx_path=word2idxpath)
    training_set.encode_dataset(training_set.word2idx, training_set.labels2idx)

    print("==========Validation Dataset==========")
    dev_file_path = join(DATA_PATH, 'dev.tsv')
    validation_set = TSVDatasetParser(dev_file_path, verbose=False, max_len=80, is_crf=crf_model)
    validation_set.encode_dataset(training_set.word2idx, training_set.labels2idx)

    print("==========Testing Dataset==========")
    test_file_path = join(DATA_PATH, 'test.tsv')
    testing_set = TSVDatasetParser(test_file_path, verbose=False, max_len=80, is_crf=crf_model)
    testing_set.encode_dataset(training_set.word2idx, training_set.labels2idx)

    return training_set, validation_set, testing_set


if __name__ == '__main__':
    RESOURCES_PATH = join(getcwd(), 'resources')
    configure_workspace(seed=1873337)
    crf_model = True
    train_dataset, dev_dataset, test_dataset = prepare_data(crf_model)

    batch_size = 64
    pretrained_embeddings = None

    embeddings_path = join(RESOURCES_PATH, 'wiki.en.vec')
    pretrained_embeddings = load_pretrained_embeddings(embeddings_path,
                                                       train_dataset.word2idx,
                                                       300, is_crf=crf_model)

    name_ = 'LSTM_CRF' if crf_model else 'LSTM'
    hp = HyperParameters(name_, train_dataset.word2idx,
                         train_dataset.labels2idx,
                         pretrained_embeddings,
                         batch_size)

    # train_dataset_ = DataLoader(dataset=train_dataset, batch_size=batch_size, collate_fn=pad_per_batch)
    train_dataset_ = DataLoader(dataset=train_dataset, batch_size=batch_size)
    dev_dataset_ = DataLoader(dataset=dev_dataset, batch_size=batch_size)
    test_dataset_ = DataLoader(dataset=test_dataset, batch_size=batch_size)

    if not crf_model:
        model = BaselineModel(hp).to(train_dataset.get_device)
        print(f'\n========== Model Summary ==========\n{torch_summarize(model)}')

        trainer = Trainer(
            model=model,
            loss_function=CrossEntropyLoss(ignore_index=train_dataset.labels2idx['<PAD>']),
            optimizer=Adam(model.parameters()),
            batch_num=hp.batch_size,
            num_classes=hp.num_classes,
            verbose=True
        )
        save_to_ = join(RESOURCES_PATH, f"{model.name}_model.pt")
        trainer.train(train_dataset_, dev_dataset_, epochs=1, save_to=save_to_)
    else:
        model = CRF_Model(hp).to(train_dataset.get_device)
        print(f'========== Model Summary ==========\n{torch_summarize(model)}')
        model_num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Num of Parameters:  {model_num_params}")

        log_path = join(getcwd(), 'runs', hp.model_name)
        writer_ = WriterTensorboardX(log_path, logger=logging, enable=True)

        trainer = CRF_Trainer(
            model=model,
            loss_function=CrossEntropyLoss(ignore_index=train_dataset.labels2idx['<PAD>']),
            optimizer=Adam(model.parameters()),
            label_vocab=train_dataset.labels2idx,
            writer=writer_
        )
        trainer.train(train_dataset_, dev_dataset_, epochs=1)
        model.save_checkpoint(join(RESOURCES_PATH, f"{model.name}_model.pt"))

    evaluator = Evaluator(model, test_dataset_, crf_model)
    evaluator.check_performance(train_dataset.idx2label)
