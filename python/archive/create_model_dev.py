#!/usr/bin/env python3
import sys
import os
import argparse
import numpy as np
import tensorflow as tf
import json
import prepare_image
import utility
import h5py
import keras

from keras.models import Sequential, Model, model_from_json
from keras.layers import Dense, Flatten, Dropout, Input, concatenate, merge, Add, Dropout
from keras.layers import Conv2D, Conv2DTranspose, Cropping2D, ZeroPadding2D, Activation
from keras.layers import MaxPooling2D, UpSampling2D, Permute
from keras import backend as K
from keras.activations import softmax
import keras.backend.tensorflow_backend as tfb
from keras.utils import plot_model
from keras.preprocessing.sequence import pad_sequences
from keras.optimizers import SGD,Adam
from time import time

K.set_image_data_format("channels_first")
cur_dir = os.getcwd()


def image_accuracy(y_true, y_pred):
    with tf.name_scope("ImageAccuracy"):
        X_sigmoid = tf.nn.sigmoid(y_true, name="Sigmoid")
        X_softmax = tf.nn.softmax(X_sigmoid, axis=1, name="Softmax")
        verify = tf.cast(tf.equal(tf.argmax(X_softmax, axis=1),
                                  tf.argmax(y_pred, axis=1), name="Compare"),
                         dtype=tf.float32, name="Cast")
        accuracy = tf.reduce_mean(verify, name="Accuracy")
        return accuracy


def sigmoid_cross_entropy_with_logits(target, output):
    with tf.name_scope("SigmoidCrossEntropyLoss"):
        # print(target.get_shape())
        loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=target,
                                                   logits=output, name="SigmoidCrossEntropy")
        return tf.reduce_mean(loss, axis=1, name="LossMean")


def softmax_cross_entropy_with_logits(target, output):
    with tf.name_scope("SigmoidCrossEntropyLoss"):
        loss = tf.nn.softmax_cross_entropy_with_logits_v2(labels=target,
                                                          logits=output,
                                                          dim=1
                                                          )
        return tf.reduce_mean(loss, axis=-1)


def parse_args():
    """
        function for argument parsing
        :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", "-c", help="Cache data wherever possible", action='store_true')
    parser.add_argument("--classification", "-t", help="Cache data wherever possible",
                        default=4, type=int)
    parser.add_argument("--dataset", "-d", help="dataset small or big",
                         default="big", choices=["small", "big"], type=str)
    parser.add_argument("--reload", "-r", help="reload data", action='store_true')
    parser.add_argument("--activation", "-a", help="activation function for conv layers",
                         default="relu")
    parser.add_argument("--log_level", "-l", help="Set loglevel for debugging and analysis",
                         default="INFO")
    args = parser.parse_args()
    return args


class RetinaModel(object):
    def __init__(self, classification=3, dataset="big", reload="False", activation='relu'):
        self.model = None
        self.input = None
        self.output = None
        self._classification = classification
        self.dataset = dataset
        self.reload = reload
        self.activation = activation

    def create_model(self):
        print(self.activation)
        input_shape =(3, 565, 565)

        data_input = Input(shape=input_shape, name="data_input")
        conv1_1 = Conv2D(64, kernel_size=(3, 3), activation=self.activation, name="conv1_1",
                          padding="SAME")(data_input)
        conv1_1 = Dropout(0.2, name="Drop1_1")(conv1_1)
        conv1_2 = Conv2D(64, kernel_size=(3, 3), activation=self.activation, name="conv1_2",
                          padding="SAME")(conv1_1)
        conv1_2 = Dropout(0.2, name="Drop1_2")(conv1_2)
        max_pool1 = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), name='max_pool1',
                                  padding="SAME")(conv1_2)

        # Convolution Layer 2
        conv2_1 = Conv2D(128, kernel_size=(3, 3), activation=self.activation, name="conv2_1",
                          padding="SAME")(max_pool1)
        conv2_1 = Dropout(0.2, name="Drop2_1")(conv2_1)
        conv2_2 = Conv2D(128, kernel_size=(3, 3), activation=self.activation, name="conv2_2",
                          padding="SAME")(conv2_1)
        conv2_2 = Dropout(0.2, name="Drop2_2")(conv2_2)
        max_pool2 = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), name='max_pool2',
                                  padding="SAME")(conv2_2)

        # Convolution Layer3
        conv3_1 = Conv2D(256, kernel_size=(3, 3), activation=self.activation, name="conv3_1",
                          padding="SAME")(max_pool2)
        conv3_1 = Dropout(0.2, name="Drop3_1")(conv3_1)
        conv3_2 = Conv2D(256, kernel_size=(3, 3), activation=self.activation, name="conv3_2",
                          padding="SAME")(conv3_1)
        conv3_2 = Dropout(0.2, name="Drop3_2")(conv3_2)
        conv3_3 = Conv2D(256, kernel_size=(3, 3), activation=self.activation, name="conv3_3",
                          padding="SAME")(conv3_2)
        conv3_3 = Dropout(0.2, name="Drop3_3")(conv3_3)
        max_pool3 = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), name='max_pool3',
                                  padding="SAME")(conv3_3)

        # Convolution Layer4
        conv4_1 = Conv2D(512, kernel_size=(3, 3), activation=self.activation, name="conv4_1",
                          padding="SAME")(max_pool3)
        conv4_1 = Dropout(0.2, name="Drop4_1")(conv4_1)
        conv4_2 = Conv2D(512, kernel_size=(3, 3), activation=self.activation, name="conv4_2",
                          padding="SAME")(conv4_1)
        conv4_2 = Dropout(0.2, name="Drop4_2")(conv4_2)
        conv4_3 = Conv2D(512, kernel_size=(3, 3), activation=self.activation, name="conv4_3",
                          padding="SAME")(conv4_2)
        conv4_3 = Dropout(0.2, name="Drop4_3")(conv4_3)

        conv5_1 = Conv2D(64, kernel_size=(5, 5), activation=self.activation, name="conv5_1",
                          padding="SAME")(max_pool1)
        conv5_1 = Dropout(0.2, name="Drop5_1")(conv5_1)
        conv5_2 = Conv2D(64, kernel_size=(5, 5), activation=self.activation, name="conv5_2",
                          padding="SAME")(conv5_1)
        conv5_2 = Dropout(0.2, name="Drop5_2")(conv5_2)
        max_pool4 = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), name='max_pool4',
                                  padding="SAME")(conv5_2)

        # Convolution Layer 2
        conv6_1 = Conv2D(128, kernel_size=(5, 5), activation=self.activation, name="conv6_1",
                          padding="SAME")(max_pool4)
        conv6_1 = Dropout(0.2, name="Drop6_1")(conv6_1)
        conv6_2 = Conv2D(128, kernel_size=(3, 3), activation=self.activation, name="conv6_2",
                          padding="SAME")(conv6_1)
        conv6_2 = Dropout(0.2, name="Drop6_2")(conv6_2)
        max_pool5 = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), name='max_pool5',
                                  padding="SAME")(conv6_2)

        #
        conv1_2_16 = Conv2D(16, kernel_size=(3, 3), name="conv1_2_16",
                             padding="SAME")(conv1_2)
        conv1_2_16 = Dropout(0.2, name="Drop1_2_16")(conv1_2_16)
        conv2_2_16 = Conv2D(16, kernel_size=(3, 3), name="conv2_2_16",
                             padding="SAME")(conv2_2)
        conv2_2_16 = Dropout(0.2, name="Drop2_2_16")(conv2_2_16)
        conv3_3_16 = Conv2D(16, kernel_size=(3, 3), name="conv3_3_16",
                             padding="SAME")(conv3_3)
        conv3_3_16 = Dropout(0.2, name="Drop3_3_16")(conv3_3_16)
        conv4_3_16 = Conv2D(16, kernel_size=(3, 3), name="conv4_3_16",
                             padding="SAME")(conv4_3)
        conv4_3_16 = Dropout(0.2, name="Drop4_3_16")(conv4_3_16)

        conv5_2_16 = Conv2D(16, kernel_size=(3, 3), name="conv5_2_16",
                             padding="SAME")(conv5_2)
        conv5_2_16 = Dropout(0.2, name="Drop5_2_16")(conv5_2_16)
        conv6_2_16 = Conv2D(16, kernel_size=(3, 3), name="conv6_2_16",
                             padding="SAME")(conv6_2)
        conv6_2_16 = Dropout(0.2, name="Drop6_2_16")(conv6_2_16)
        

        # Deconvolution Layer1
        side_multi2_up = UpSampling2D(size=(2, 2), name="side_multi2_up")(conv2_2_16)

        upside_multi2 = Cropping2D(cropping=((0, 1),(0, 1)), name="upside_multi2")(side_multi2_up)

        #Decovolution Layer2
        side_multi3_up = UpSampling2D(size=(4, 4), name="side_multi3_up")(conv3_3_16)
        upside_multi3 = Cropping2D(cropping=((1, 2),(1, 2)), name="upside_multi3")(side_multi3_up)

        # Deconvolution Layer3
        side_multi4_up = UpSampling2D(size=(8, 8), name="side_multi4_up")(conv4_3_16)
        upside_multi4 = Cropping2D(cropping=((1, 2),(1, 2)), name="upside_multi4")(side_multi4_up)

        # Deconvolution Layer4
        side_multi5_up = UpSampling2D(size=(2, 2), name="side_multi5_up")(conv5_2_16)

        upside_multi5 = Cropping2D(cropping=((0, 1),(0, 1)), name="upside_multi5")(side_multi5_up)

        # Deconvolution Layer1
        side_multi6_up = UpSampling2D(size=(4, 4), name="side_multi6_up")(conv6_2_16)

        upside_multi6 = Cropping2D(cropping=((1, 2),(1, 2)), name="upside_multi6")(side_multi6_up)

        # Specialized Layer
        concat_upscore = concatenate([conv1_2_16, upside_multi2, upside_multi3, upside_multi4, 
                                      upside_multi5, upside_multi6],
                                      name="concat-upscore", axis=1)
        upscore_fuse = Conv2D(self._classification, kernel_size=(1, 1), name="upscore_fuse")(concat_upscore)
        upscore_fuse = Dropout(0.2, name="Dropout_Classifier")(upscore_fuse)

        self.model = Model(inputs=[data_input], outputs=[upscore_fuse])


    def set_weights(self):
        if args.cache and os.path.exists("cache/keras_crop_model_weights_4class_dev_reg_relu.h5"):
            self.model.load_weights("cache/keras_crop_model_weights_4class_dev_reg_relu.h5")
            return
            with open("cache/4_class_model.json") as f:
                model_4class = model_from_json(json.dumps(json.load(f)))
            model_4class.load_weights("cache/keras_crop_model_weights_4class_reg.h5")

            for layer, layer4 in zip(self.model.layers, model_4class.layers):
                if layer.name == layer4.name:
                    layer.set_weights(layer4.get_weights())

    def _write_hdf5(self, name, data):
        output_file = os.path.join(self.cache_image, name+'.h5')
        with h5py.File(output_file, "w") as f:
            f.create_dataset('image', data=data, dtype=data.dtype)

    @staticmethod
    def _load_hdf5(input_file):
        with h5py.File(input_file, "r") as f:  # "with" close the file after its nested commands
            return f["image"][()]

    def get_data(self):
        self.cache_image = os.path.join(pylon5_cache, self.dataset, 'image')
        if self.reload:
            utility.remove_directory(self.cache_image)
        if args.cache and os.path.exists(self.cache_image):
            # print(self.cache_image);exit()
            self.train_images = self._load_hdf5(os.path.join(self.cache_image, 'train_images.h5'))
            self.train_labels = self._load_hdf5(os.path.join(self.cache_image, 'train_labels.h5'))
            self.test_images = self._load_hdf5(os.path.join(self.cache_image, 'test_images.h5'))
            self.test_labels = self._load_hdf5(os.path.join(self.cache_image, 'test_labels.h5'))
            return

        self.train_images = prepare_image.load_images(data_type="train", image_type="image",
                                                      classification=self._classification,
                                                      dataset = self.dataset)
        self.train_labels = prepare_image.load_images(data_type="train", image_type="label",
                                                      classification=self._classification,
                                                      dataset=self.dataset)
        self.test_images = prepare_image.load_images(data_type="test", image_type="image",
                                                     classification=self._classification,
                                                     dataset=self.dataset)
        self.test_labels = prepare_image.load_images(data_type="test", image_type="label",
                                                     classification=self._classification,
                                                     dataset=self.dataset)
        return
        if args.cache and not os.path.exists(self.cache_image):
            utility.create_directory(self.cache_image)
            self._write_hdf5('train_images', self.train_images)
            self._write_hdf5('train_labels', self.train_labels)
            self._write_hdf5('test_images', self.test_images)
            self._write_hdf5('test_labels', self.test_labels)

    def run(self):
        print(self.train_images.shape)
        sgd = SGD(lr=1e-3, decay=1e-4, momentum=0.9, nesterov=True)
        weight_save_callback = keras.callbacks.ModelCheckpoint('/cache/checkpoint_weights.h5', monitor='val_loss',
                                                verbose=0, save_best_only=True, mode='auto')
        tb_callback = keras.callbacks.TensorBoard(log_dir='./Graph/{}/'.format(time()), histogram_freq=20,
                                     write_graph=True, write_images=False)
        # tb_callback.set_model(self.model)
        # weight_save_callback.set_model(self.model)
        self.model.compile(optimizer=sgd, loss=sigmoid_cross_entropy_with_logits,
                            metrics=['accuracy',image_accuracy])

        # self.model.fit(self.train_images[:1, ...], self.train_labels[:1, ...], batch_size=1, epochs=1,
        #               callbacks=[tb_callback], verbose=1)
        self.model.fit(self.train_images, self.train_labels, batch_size=5, epochs=1000,
                        callbacks=[tb_callback], validation_split=0.05, verbose=1)

        self.model.save_weights(os.path.join('cache', 'keras_crop_model_weights_4class_dev_reg_{}.h5'.format(self.activation)))

    def predict(self):
        test_predict = self.model.predict(self.test_images, batch_size=10)
        print(test_predict[0])
        print(test_predict.shape)
        np.save('cache/test_predict2_class_4_{}.npy'.format(self.activation), test_predict)


if __name__ == '__main__':
    pylon5 = os.environ["SCRATCH"] if os.environ.get("SCRATCH", None) else "."
    pylon5_cache = os.path.join(pylon5, 'cache')
    args = parse_args()
    rm = RetinaModel(classification=args.classification, dataset=args.dataset,
                     reload=args.reload, activation=args.activation)
    rm.create_model()

    rm.set_weights()

    rm.get_data()
    print(rm.test_labels.shape)
    print(rm.train_images.shape)
    # print(rm.model.layers[1].get_weights())
    # print(rm.model.layers[1].output_shape)
    # plot_model(rm.model,"model.png")
    # rm.run()
    rm.predict()

    # plot_model(rm.model, "model.png")
    print(rm.model.summary())
    K.clear_session()
