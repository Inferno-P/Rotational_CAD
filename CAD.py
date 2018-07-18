from keras.models import Model
from keras.layers import Input, Dense, Conv1D, Conv2D, MaxPooling2D, Conv2DTranspose, Flatten,Reshape, UpSampling2D, Cropping2D
from keras.callbacks import ModelCheckpoint, EarlyStopping
import h5py
import numpy as np
import sys

"""
Sample running command:
python3 CAD.py model_type input_data output_path
"""

input_data_path = sys.argv[2]
output_path = sys.argv[3]

"""
Different models to try out
"""
def getModel_1():
    """
    Flat model
    :return:
    """
    input_img = Input(shape=(1, 28, 28))
    x = Flatten()(input_img)
    x = Dense(512, activation='relu')(x)
    x = Dense(256, activation='relu')(x)
    x = Dense(512, activation='relu')(x)
    x = Dense(784, activation='sigmoid')(x)
    output = Reshape((1,28,28))(x)
    model = Model(input_img, output)

    return model

def getModel_deconv():
    """
    Convolutional auto encoder with transposed convolutions
    :return:
    """
    input_img = Input(shape=(1,28,28))
    x = Conv2D(4,(3,3),
               activation='relu',
               data_format='channels_first')(input_img) # Size 4x26x26
    x = Conv2D(4,(3,3),
               activation='relu',
               data_format='channels_first')(x) # Size 4x24x24
    x = Conv2D(8,(3,3),
               activation='relu',
               data_format='channels_first')(x) # Size 8x22x22
    x = Conv2D(8,(3,3),
               activation='relu',
               data_format='channels_first')(x) # Size 8x20x20
    x = Flatten()(x)
    x = Dense(1024, activation='relu')(x)
    code = Dense(256, activation='relu')(x)
    x = Dense(1024, activation='relu')(code)
    x = Dense(3200, activation='relu')(x)
    x = Reshape((8,20,20))(x)
    x = Conv2DTranspose(8, (3,3),
                        activation='relu',
                        data_format='channels_first')(x) # Size 8x22x22
    x = Conv2DTranspose(8, (3,3),
                        activation='relu',
                        data_format='channels_first')(x) # Size 8x24x24
    x = Conv2DTranspose(4, (3,3),
                        activation='relu',
                        data_format='channels_first')(x) # Size 4x26x26
    decoded = Conv2DTranspose(1, (3,3),
                        activation='sigmoid',
                        data_format='channels_first')(x) # Size 1x28x28

    model = Model(input_img, decoded)
    return model

def getModel_upsample():
    """
    Convolutional auto encoder with upsampling layers
    :return:
    """
    # Input
    input_img = Input(shape=(1,28,28))
    # Encoder
    x = Conv2D(8,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(input_img)
    x = Conv2D(8,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = MaxPooling2D((2,2),
                     padding='same',
                     data_format='channels_first')(x) # Size 8x14x14
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = MaxPooling2D((2,2),
                     padding='same',
                     data_format='channels_first')(x) # Size 16x7x7
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = MaxPooling2D((2,2),
                        padding='same',
                        data_format='channels_first')(x) # Size 16x4x4

    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    # Encoded layer, Size 16x4x4
    encoded = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)

    # Decoder
    x = Conv2D(16, (3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(encoded)
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = UpSampling2D((2,2),
                     data_format='channels_first')(x)
    x = Conv2D(16, (3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = UpSampling2D((2,2),
                     data_format='channels_first')(x) # Size 16x16x16
    x = Conv2D(16, (3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = Conv2D(16,(3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = UpSampling2D((2,2),
                     data_format='channels_first')(x) # Size 8x32x32
    x = Conv2D(8, (3,3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x)
    x = Conv2D(8, (3, 3),
               activation='relu',
               padding='same',
               data_format='channels_first')(x) # Size 4x32x32
    x = Conv1D(1, 1,
             padding='same',
             activation='sigmoid',
             data_format='channels_first')(x) # Size 1x32x32
    # Crop from 1x32x32 to 1x28x28
    decoded = Cropping2D(cropping=((2,2),(2,2)),
                   data_format='channels_first')(x)

    model = Model(input_img, decoded)
    return model

"""
Training function
"""
def train(model):
    # Load datasets
    with h5py.File(input_data_path,'r') as f:
        X_train = f['X_train'][()]
        Y_train = f['Y_train'][()]
        X_valid = f['X_valid'][()]
        Y_valid = f['Y_valid'][()]

    # Add the extra channel axis
    X_train = X_train[:,np.newaxis,:,:]
    Y_train = Y_train[:, np.newaxis, :, :]
    X_valid = X_valid[:, np.newaxis, :, :]
    Y_valid = Y_valid[:, np.newaxis, :, :]

    # Callbacks
    modelcp = ModelCheckpoint(output_path+"/saved-model-{epoch:02d}-{val_loss:.4f}.hdf5",
                              save_best_only=True,
                              mode='min')
    earlystop = EarlyStopping(monitor='val_loss', patience=10)

    # Fitting
    model.fit(X_train, Y_train, validation_data=(X_valid, Y_valid),
              epochs=500,
              batch_size=128,
              shuffle=True,
              callbacks=[modelcp, earlystop],
              verbose=2)

    model.save(output_path+'/model.hdf5')


"""
Main running
"""
if __name__ == '__main__':
    if sys.argv[1] == 'flat':
        model = getModel_1()
    elif sys.argv[1] == 'convt':
        model = getModel_deconv()
    elif sys.argv[1] == 'upsample':
        model = getModel_upsample()

    print(model.summary())
    model.compile(optimizer='rmsprop', loss='mse')
    train(model)