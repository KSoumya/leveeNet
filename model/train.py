import numpy as np
import xarray as xr
import argparse
import pickle
from keras.optimizer import Adam
from keras.callbacks import TensorBoard, ReduceLROnPlateau, ModelCheckpoint, EarlyStopping
import keras.backend.tensorflow_backend as KTF
import tensorflow as tf
from model import leveeNet
import image_generator

parser = argparse.ArgumentParser(description="Train levee detection model")
parser.add_argument("-c", "--config", help="configuration file",
                    type=str, required=True)

# parse args and check data types
args = parser.parse_args()

n_classes = args.get("model","n_classes")
assert isinstance(n_classes, int), "n_classes must be int, but got {0}".format(type(n_classes))
model_outpath = args.get("model", "model_outpath")

image_size = args.get("generator", "image_size")
assert isinstance(image_size, tuple), "image_size must be tuple, but got {0}".format(type(image_size))
max_pool = args.get("generator", "max_pool")
assert (isinstance(max_pool, int)| (max_pool is None)), "max_pool must be None or int, but got {0}".format(type(max_pool))
shuffle = args.getboolean("generator", "shuffle")
augment = args.getboolean("generator", "augment")

batch_size = args.get("train", "batch_size")
assert isinstance(batch_size, int), "batch_size must be int, but got {0}".format(type(batch_size))
num_epochs = args.get("train", "num_epochs")
assert isinstance(num_epochs, int), "num_epoch must be int, but got {0}".format(type(num_epochs))
logpath = args.get("train", "log_path")
split = args.get("train", "split")

datapath = args.get("data", "data_path")

# read data as DataArray
data = xr.open_dataset(datapath)
X = data["features"]
Y = data["labels"]

# split dataset
nsamples = X.sizes["sample"]
indices = np.arange(0, nsamples, 1)
np.random.shuffle(indices)
train_indices = indices[0:int(nsamples*split)]
test_indices = indices[int(nsamples*split)::]
X_train = X.sel(sample=train_indices)
X_test = X.sel(sample=test_indices)
Y_train = Y.sel(sample=train_indices)
Y_test = Y.sel(sample=test_indices)

# instantiate generator
train_generator = image_generator.DataGenerator(X_train, Y_train,
                                                n_classes, batch_size,
                                                image_size, max_pool,
                                                shuffle, augment)
test_generator = image_generator.DataGenerator(X_test, Y_test,
                                                n_classes, batch_size,
                                                image_size, max_pool,
                                                shuffle, augment)

# callbacks
# reduces learning rate if no improvement are seen
# learning_rate_reduction = ReduceLROnPlateau(monitor='val_loss',
#                                             patience=2,
#                                             verbose=1,
#                                             factor=0.5,
#                                             min_lr=0.0000001)

# stop training if no improvements are seen
early_stop = EarlyStopping(monitor="val_loss",
                           mode="min",
                           patience=5,
                           restore_best_weights=True)

# saves model weights to file
checkpoint = ModelCheckpoint('./model_weights.hdf5',
                             monitor='val_loss',
                             verbose=1,
                             save_best_only=True,
                             mode='min',
                             save_weights_only=True)

# start session
old_session = KTF.get_session()

with tf.Graph().as_default():
    session = tf.Session('')
    KTF.set_session(session)
    # KTF.set_learning_phase(1)  # need this if you use dropout
    model = leveeNet(n_classes, image_size)
    model.compile(loss='binary_crossentropy', optimizer=Adam(), metrics=['accuracy'])

    tensorboard = TensorBoard(log_dir=logpath, histogram_freq=1)

    history = model.fit_generator(generator=train_generator,
		                          validation_data=test_generator,
		                          epochs=num_epochs,
		                          steps_per_epoch=len(train_generator),
		                          validation_steps =len(test_generator),
		                          callbacks=[tensorboard, early_stop, checkpoint],
		                          verbose=1,
		                          )
    model.save(model_outpath)
    score = model.evaluate(X_test, Y_test, verbose=0)
    print('Test score:', score[0])
    print('Test accuracy;', score[1])

KTF.set_session(old_session)