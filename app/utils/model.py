"""Neural network model architecture for plant disease detection."""
from torch import nn


def conv_block(in_channels, out_channels, pool=False):
    """
    Create a convolutional block with batch normalization and ReLU activation.

    Args:
        in_channels: Number of input channels
        out_channels: Number of output channels
        pool: Whether to add max pooling layer

    Returns:
        Sequential neural network block
    """
    layers = [
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    ]
    if pool:
        layers.append(nn.MaxPool2d(4))
    return nn.Sequential(*layers)


class ResNet9(nn.Module):
    """
    ResNet9 architecture for plant disease classification.

    A lightweight ResNet variant with 9 layers, suitable for image classification tasks.
    """

    def __init__(self, in_channels, num_diseases):
        super().__init__()

        self.conv1 = conv_block(in_channels, 64)
        self.conv2 = conv_block(64, 128, pool=True)  # out_dim : 128 x 64 x 64
        self.res1 = nn.Sequential(conv_block(128, 128), conv_block(128, 128))

        self.conv3 = conv_block(128, 256, pool=True)  # out_dim : 256 x 16 x 16
        self.conv4 = conv_block(256, 512, pool=True)  # out_dim : 512 x 4 x 44
        self.res2 = nn.Sequential(conv_block(512, 512), conv_block(512, 512))

        self.classifier = nn.Sequential(
            nn.MaxPool2d(4), nn.Flatten(), nn.Linear(512, num_diseases)
        )

    def forward(self, xb):
        """
        Forward pass through the network.

        Args:
            xb: Input batch tensor

        Returns:
            Output predictions tensor
        """
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        out = self.classifier(out)
        return out
