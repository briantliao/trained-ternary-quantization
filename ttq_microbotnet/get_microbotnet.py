import torch
import torch.nn as nn
import torch.optim as optim

import sys
from fd_mobilenet_v3 import FdMobileNetV3Imp2


def load_model(model, file_name='fd-mobilenet-v3-x0_32.pth'):
    def reformat_dict(state):
        reformat_state = {}
        for key in state:
            new_key = key.replace('module.', '')
            reformat_state[new_key] = state[key]
        return reformat_state
    state = torch.load(file_name,  map_location='cpu')['net']
    reformat_state = reformat_dict(state)
    model.load_state_dict(reformat_state)
    # do we have to return?

def get_model(learning_rate=1e-3):

    model = FdMobileNetV3Imp2(classes_num=10, input_size=32, width_multiplier=0.25, mode='small')

    # first layer is not trainable
    first_layer = model.features[0][0]
    first_layer.weight.requires_grad = False

    # last fc layer is not trainable. (NOTE: there are multiple Linear units
    # in the bottleneck layers. What should we do with them?)
    last_linear = model.classifier[1]
    weights = [last_linear.weight]
    biases = [last_linear.bias]


    # [p for n, p in model.named_parameters() if 'fc' in n]
    # what about bias


    # Only bottlenecks [1:11] are quantized
    weights_to_be_quantized = [
        p for n, p in model.features[1:11].named_parameters()
        if 'conv' in n and 'lastBN' not in n and 'fc' not in n
    ]

    # parameters of batch_norm layers
    bn_weights = [model.features[0][1].weight, model.features[11][1].weight] + \
        [
            p for n, p in model.features[1:11].named_parameters()
            if 'lastBN' in n and 'weight' in n
        ]
    bn_biases = [model.features[0][1].bias, model.features[11][1].bias] + \
        [
            p for n, p in model.features[1:11].named_parameters()
            if 'lastBN' in n and 'bias' in n
        ]

    params = [
        {'params': weights, 'weight_decay': 1e-4},
        {'params': weights_to_be_quantized},
        {'params': biases},
        {'params': bn_weights},
        {'params': bn_biases}
    ]
    optimizer = optim.Adam(params, lr=learning_rate)

    loss = nn.CrossEntropyLoss().cuda()
    model = model.cuda()  # move the model to gpu
    return model, loss, optimizer