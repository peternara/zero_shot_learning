#Partialy based on https://kratzert.github.io/2017/02/24/finetuning-alexnet-with-tensorflow.html

import tensorflow as tf
import numpy as np
import pickle
import os
from datetime import datetime
from models import Devise
from batch_making import *

initial_learning_rate = 0.1
momentum = 0.9
num_epochs = 300
batch_size = 128

dropout_rate = 0.5
num_classes = 60
word2vec_size = 100
train_layers = ['conv1', 'conv2', 'proj']

display_step = 1

filewriter_path = 'cifar100_devise_history/'
checkpoint_path = 'checkpoints_devise/'

IMAGE_SIZE = 24
OUTPUT_FILE_NAME = 'train_output_devise.txt'

decay_steps = int(len(target_train_data)/batch_size)
learning_rate_decay_factor = 0.95

if not os.path.isdir(filewriter_path): os.mkdir(filewriter_path)
if not os.path.isdir(checkpoint_path): os.mkdir(checkpoint_path)

x = tf.placeholder(tf.float32, [batch_size, IMAGE_SIZE, IMAGE_SIZE, 3])
y = tf.placeholder(tf.float32, [None, word2vec_size])

model = Devise(x, num_classes, word2vec_size)
model_output = model.projection_layer

var_list = [v for v in tf.trainable_variables() if v.name.split('/')[0] in train_layers]

def distort_image(image):
      distorted_image = tf.random_crop(image, [IMAGE_SIZE, IMAGE_SIZE, 3])
      distorted_image = tf.image.random_flip_left_right(distorted_image)
      distorted_image = tf.image.random_brightness(distorted_image,
                                               max_delta=63)
      distorted_image = tf.image.random_contrast(distorted_image,
                                             lower=0.2, upper=1.8)
      float_image = tf.image.per_image_standardization(distorted_image)
      return float_image

def distorted_batch(batch):
    return tf.map_fn(lambda frame: distort_image(frame), batch)

initial_x_batch = tf.placeholder(tf.float32, [batch_size, IMAGE_SIZE, IMAGE_SIZE, 3])
dist_x_batch = distorted_batch(initial_x_batch)

def print_in_file(string):
    output_file = open(OUTPUT_FILE_NAME, 'a')
    output_file.write(string + '\n')
    print(string)
    output_file.close()

with tf.name_scope("loss"):
    loss = tf.reduce_sum(tf.pow(model_output-y, 2))/(2*batch_size)
   
with tf.name_scope('train'):
    gradients = tf.gradients(loss, var_list)
    gradients = list(zip(gradients, var_list))
    global_step = tf.Variable(0)
    
    learning_rate = initial_learning_rate
    #tf.train.exponential_decay(initial_learning_rate,
    #                              global_step,
    #                              decay_steps,
    #                              learning_rate_decay_factor,
    #                              staircase=True)

    optimizer = tf.train.MomentumOptimizer(learning_rate, momentum)
    train_op = optimizer.apply_gradients(grads_and_vars=gradients, global_step=global_step)

# Initialize an saver for store model checkpoints
saver = tf.train.Saver()
variables_to_restore = [v for v in tf.trainable_variables() if 'proj' not in v.name.split('/')[0]]

previous_loader = tf.train.Saver(variables_to_restore)

# Initalize the data generator seperately for the training and validation set
train_generator = get_batches(target_train_data, batch_size, IMAGE_SIZE, word2vec=True)
val_generator = get_batches(target_test_data, batch_size, IMAGE_SIZE, word2vec=True)

# Start Tensorflow session
with tf.Session() as sess:

  # Initialize all variables
  sess.run(tf.global_variables_initializer())

  # Load the pretrained weights into the non-trainable layer
  previous_loader.restore(sess, 'checkpoints_old2/model_epoch42.ckpt')

  print_in_file("{} Start training...".format(datetime.now()))
  print_in_file("{} Open Tensorboard at --logdir {}".format(datetime.now(),
                                                    filewriter_path))

  # Loop over number of epochs
  for epoch in range(num_epochs):

    print_in_file("{} Epoch number: {}".format(datetime.now(), epoch+1))

    for batch_xs, batch_ys in train_generator:

        # And run the training op
        new_batch = sess.run(dist_x_batch, feed_dict={initial_x_batch: batch_xs})
        
        sess.run(train_op, feed_dict={x: new_batch,
                                          y: batch_ys})


    # Validate the model on the entire validation set
    print_in_file("{} Start validation".format(datetime.now()))
    test_loss = 0.
    test_count = 0
    
    for batch_tx, batch_ty in val_generator:
        new_loss = sess.run(loss, feed_dict={x: batch_tx,
                                                y: batch_ty})
        test_loss += new_loss
        test_count += 1
    test_loss /= test_count

    print_in_file("Validation Loss = %s %.4f" % (datetime.now(), test_loss))
    
    # Reset the file pointer of the image data generator
    train_generator = get_batches(target_train_data, batch_size, IMAGE_SIZE, word2vec=True)
    val_generator = get_batches(target_test_data, batch_size, IMAGE_SIZE, word2vec=True)

    print_in_file("{} Saving checkpoint of model...".format(datetime.now()))

    #save checkpoint of the model
    checkpoint_name = os.path.join(checkpoint_path, 'model_epoch'+str(epoch)+'.ckpt')
    save_path = saver.save(sess, checkpoint_name)

    print_in_file("{} Model checkpoint saved at {}".format(datetime.now(), checkpoint_name))