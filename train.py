import tensorflow as tf
from tensorflow.python.training import queue_runner
import numpy as np
import argparse
import srgan
import os
from utilities import build_inputs, downsample_batch, build_log_dir, preprocess

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--load', type=str, help='Checkpoint to load all weights from.')
  parser.add_argument('--name', type=str, help='Name of experiment')
  parser.add_argument('--batch-size', type=int, default=20, help='Mini-batch size.')
  parser.add_argument('--learning-rate', type=float, default=1e-4, help='Learning rate for Adam.')
  parser.add_argument('--content-loss', type=str, choices=['mse', 'vgg22', 'vgg54'], 'Metric to use for content loss.')
  parser.add_argument('--use-gan', action='store_true', 'Add adversarial loss term to generator and trains discriminator.')
  parser.add_argument('--image-size-train', type=int, default=96, help='Dimensions of training images.')
  parser.add_argument('--image-size-test', type=int, default=96, help='Dimensions of testing images.')
  parser.add_argument('--num-test', type=int, default=1000, help='Number of images to test on.')
  args = parser.parse_args()
  
  # Set up models
  training = tf.placeholder(tf.bool)
  discriminator = srgan.SRGanDiscriminator()
  generator = srgan.SRGanGenerator(discriminator=discriminator, learning_rate=args.learning_rate, content_loss=args.content_less, use_gan=args.use_gan)
  # Generator
  g_x = tf.placeholder(tf.float32, [None, None, None, 3], name='input_lowres')
  g_y = tf.placeholder(tf.float32, [None, None, None, 3], name='input_highres')
  g_y_pred = generator.forward(g_x)
  g_loss = generator.loss_function(g_y, g_y_pred)
  g_train_step = generator.optimize(g_loss)
  # Discriminator
  d_x_real = tf.placeholder(tf.float32, [None, None, None, 3]), name='input_real']
  d_y_real_pred = discriminator.forward(d_x_real, reuse=True)
  d_y_fake_pred = discriminator.forward(g_y_pred, reuse=True)
  d_loss = discriminator.loss_function(d_y_real_pred, d_y_fake_pred)
  d_train_step = discriminator.optimize(d_loss)
  
  # test
  [print(x.name) for x in tf.global_variables()]

  # TODO create log folder
  log_path = build_log_dir()

  with tf.Session() as sess:
    # Build input pipeline
    get_train_batch, get_val_batch, get_eval_batch, val_data, eval_data = build_inputs(args, sess)
    # Initialize
    sess.run(tf.local_variables_initializer())
    sess.run(tf.global_variables_initializer())
    # Start input pipeline thread(s)
    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)

    # Load saved weights
    iteration = 0
    saver = tf.train.Saver()
    if args.load:
      iteration = int(args.load.split('-')[-1])
      saver.restore(sess, args.load)

    # Train
    while True:
      if iteration % args.log_freq == 0:
        # TODO Test
        # Save checkpoint
        saver.save(sess, log_path, global_step=iteration, write_meta_graph=False)

      # Get data
      batch_hr = sess.run(get_train_batch)
      batch_lr = downsample_batch(batch_y, factor=4)
      batch_lr, batch_hr = generator.preprocess(batch_lr, batch_hr)

      # Train discriminator
      if args.use_gan:
        sess.run(d_train_step, feed_dict={training: True, g_x: batch_lr, d_x_real: batch_hr})
      # Train generator
      sess.run(g_train_step, feed_dict={training: True, g_x: batch_lr, g_y: batch_hr})

      iteration += 1

    # Stop queue threads
    coord.request_stop()
    coord.join(threads)

  
if __name__ == "__main__":
  main()