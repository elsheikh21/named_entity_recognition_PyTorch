import io
import os
import torch
from torch.nn.modules.module import _addindent
import numpy as np
import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from models import BaselineModel


def save_checkpoint(state, is_best, filename='/output/checkpoint.pth.tar'):
    if is_best:
        print("Saving a new best model")
        torch.save(state, filename)  # save checkpoint


def load_checkpoint(resume_weights_path, hyperparams):
    cuda = torch.cuda.is_available()
    if cuda:
        checkpoint = torch.load(resume_weights_path)

    start_epoch = checkpoint['epoch']
    best_validation_loss = checkpoint['best_val_loss']
    model = BaselineModel(hyperparams)
    model.load_state_dict(checkpoint['state_dict'])
    print(
        f"loaded checkpoint '{checkpoint}' (trained for {start_epoch} epochs, val loss: {best_validation_loss})")
    return model


def load_pretrained_embeddings(file_name, word2idx, embeddings_size, is_crf=False):
    fin = io.open(file_name, 'r', encoding='utf-8', newline='\n', errors='ignore')
    data = {}
    for line in tqdm(fin, desc=f'Reading data from {file_name}'):
        tokens = line.rstrip().split(' ')
        data[tokens[0]] = np.array(tokens[1:], dtype=np.float)

    pretrained_embeddings = torch.randn(len(word2idx), embeddings_size)
    initialised = 0
    for idx, word in enumerate(data):
        if word in word2idx:
            initialised += 1
            vector_ = torch.from_numpy(data[word])
            pretrained_embeddings[word2idx.get(word)] = vector_

    pretrained_embeddings[word2idx["<PAD>"]] = torch.zeros(embeddings_size)
    pretrained_embeddings[word2idx["<UNK>"]] = torch.zeros(embeddings_size)
    if is_crf:
        pretrained_embeddings[word2idx["<BOS>"]] = torch.zeros(embeddings_size)
        pretrained_embeddings[word2idx["<EOS>"]] = torch.zeros(embeddings_size)
    print(f'Loaded {initialised} vectors and instantiated random embeddings for {len(word2idx) - initialised}')
    return pretrained_embeddings


def plot_history(history):
    loss_list = [s for s in history['loss']]
    val_loss_list = [s for s in history['val_loss']]

    if len(loss_list) == 0:
        print('Loss is missing in history')
        return

    # As loss always exists
    epochs = [i for i in range(1, len(history['loss']) + 1)]

    # Loss
    plt.figure(1)
    plt.plot(epochs, loss_list, label="loss")
    plt.plot(epochs, val_loss_list, label="val_loss")

    plt.title('Training Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.savefig(os.path.join(os.getcwd(), 'resources', 'loss_plot.png'))
    plt.show()


def torch_summarize(model, show_weights=True, show_parameters=True):
    """Summarizes torch model by showing trainable parameters and weights."""
    tmpstr = model.__class__.__name__ + ' (\n'
    for key, module in model._modules.items():
        # if it contains layers let call it recursively to get params and weights
        if type(module) in [
            torch.nn.modules.container.Container,
            torch.nn.modules.container.Sequential
        ]:
            modstr = torch_summarize(module)
        else:
            modstr = module.__repr__()
        modstr = _addindent(modstr, 2)

        params = sum([np.prod(p.size()) for p in module.parameters()])
        weights = tuple([tuple(p.size()) for p in module.parameters()])

        tmpstr += '  (' + key + '): ' + modstr
        if show_weights:
            tmpstr += ', weights={}'.format(weights)
        if show_parameters:
            tmpstr +=  ', parameters={}'.format(params)
        tmpstr += '\n'

    tmpstr = tmpstr + ')'
    return tmpstr
