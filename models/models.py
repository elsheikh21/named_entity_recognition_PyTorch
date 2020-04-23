import torch
import torch.nn as nn
from torchcrf import CRF


class BaselineModel(nn.Module):
    def __init__(self, hparams):
        super(BaselineModel, self).__init__()
        self.name = 'BiLSTM'
        self.word_embedding = nn.Embedding(
            hparams.vocab_size, hparams.embedding_dim)
        if hparams.embeddings is not None:
            print("initializing embeddings from pretrained")
            self.word_embedding.weight.data.copy_(hparams.embeddings)

        self.lstm = nn.LSTM(hparams.embedding_dim, hparams.hidden_dim,
                            bidirectional=hparams.bidirectional,
                            num_layers=hparams.num_layers,
                            dropout=hparams.dropout if hparams.num_layers > 1 else 0)

        lstm_output_dim = hparams.hidden_dim if hparams.bidirectional is False else hparams.hidden_dim * 2
        self.dropout = nn.Dropout(hparams.dropout)
        self.classifier = nn.Linear(lstm_output_dim, hparams.num_classes)

    def forward(self, x):
        # [Samples_Num, Seq_Len]
        embeddings = self.word_embedding(x)
        # [Samples_Num, Seq_Len]
        o, _ = self.lstm(embeddings)
        # [Samples_Num, Seq_Len, Tags_Num]
        o = self.dropout(o)
        # [Samples_Num, Seq_Len, Tags_Num]
        logits = self.classifier(o)
        # [Samples_Num, Seq_Len]
        return logits


class CRF_Model(nn.Module):
    def __init__(self, hparams):
        super(CRF_Model, self).__init__()
        self.name = 'CRF_BiLSTM'
        self.word_embedding = nn.Embedding(
            hparams.vocab_size, hparams.embedding_dim)
        if hparams.embeddings is not None:
            print("initializing embeddings from pretrained")
            self.word_embedding.weight.data.copy_(hparams.embeddings)

        self.lstm = nn.LSTM(hparams.embedding_dim, hparams.hidden_dim,
                            bidirectional=hparams.bidirectional,
                            num_layers=hparams.num_layers,
                            dropout=hparams.dropout if hparams.num_layers > 1 else 0,
                            batch_first=True)

        lstm_output_dim = hparams.hidden_dim if hparams.bidirectional is False else hparams.hidden_dim * 2
        self.dropout = nn.Dropout(hparams.dropout)
        self.classifier = nn.Linear(lstm_output_dim, hparams.num_classes)
        self.crf = CRF(hparams.num_classes, batch_first=True)

    def forward(self, x):
        # [Samples_Num, Seq_Len]
        embeddings = self.word_embedding(x)
        # [Samples_Num, Seq_Len]
        o, _ = self.lstm(embeddings)
        # [Samples_Num, Seq_Len, Tags_Num]
        o = self.dropout(o)
        # [Samples_Num, Seq_Len, Tags_Num]
        logits = self.classifier(o)
        # [Samples_Num, Seq_Len]
        return logits

    def log_probs(self, x, tags, mask=None):
        emissions = self(x)
        return self.crf(emissions, tags, mask=mask)

    def predict(self, x):
        emissions = self(x)
        return self.crf.decode(emissions)

    def save_checkpoint(self, model_path):
        torch.save(self, model_path)
        model_checkpoint = model_path.replace('.pt', '.pth')
        torch.save(self.state_dict(), model_checkpoint)

    def load_model(self, path):
        state_dict = torch.load(path)
        self.load_state_dict(state_dict)
