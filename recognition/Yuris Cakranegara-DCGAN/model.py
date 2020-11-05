import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.layers import Dense,Reshape,Dropout,LeakyReLU,Flatten,BatchNormalization,Conv2D,Conv2DTranspose
from tensorflow.keras.models import Sequential

class OasisDCGAN:
    def __init__(self, codings_size=100, result_dir="./"):
        """Creates a DCGAN model.

        Args:
            codings_size (int, optional): The length of noise to generate the resulting image. Defaults to 100.
            result_dir (str, optional): The directory to store the resulting image. Defaults to "./" which refers to the current directory.
        """
        assert type(codings_size) == int, \
            "codings_size has to be an integer."
        assert result_dir[-1] == "/", \
            "Data directory has to end with a forward slash (/)."

        self.codings_size = codings_size
        self.generator = self.__generator()
        self.discriminator = self.__discriminator()
        self.result_dir = result_dir

        # Construct the GAN model
        self.model = Sequential([self.generator, self.discriminator])

        # Set the discriminator to be non-trainable before compiling the GAN model
        self.discriminator.compile(loss="binary_crossentropy", optimizer="adam")
        self.discriminator.trainable = False

        # Compile the GAN model
        self.model.compile(loss="binary_crossentropy", optimizer="adam")

    def __generator(self):
        generator = Sequential()
        generator.add(Dense(16 * 16 * 256, input_shape=[self.codings_size]))
        generator.add(Reshape([16, 16, 256]))
        generator.add(BatchNormalization())
        generator.add(Conv2DTranspose(128, kernel_size=4, strides=2, padding="same", activation="relu"))
        generator.add(Conv2DTranspose(64, kernel_size=4, strides=2, padding="same", activation="relu"))
        generator.add(Conv2DTranspose(32, kernel_size=4, strides=2, padding="same", activation="relu"))
        generator.add(BatchNormalization())
        generator.add(Conv2DTranspose(1, kernel_size=4, strides=2, padding="same", activation="tanh"))

        return generator

    def __discriminator(self):
        discriminator = Sequential()
        discriminator.add(Conv2D(32, kernel_size=4, strides=2, padding="same", \
                                activation=LeakyReLU(0.3), input_shape=[256, 256, 1]))
        discriminator.add(Dropout(0.3))
        discriminator.add(Conv2D(64, kernel_size=4, strides=2, padding="same", activation=LeakyReLU(0.3)))
        discriminator.add(Dropout(0.3))
        discriminator.add(Conv2D(128, kernel_size=4, strides=2, padding="same", activation=LeakyReLU(0.3)))
        discriminator.add(Dropout(0.3))
        discriminator.add(Flatten())
        discriminator.add(Dense(1, activation="sigmoid"))

        return discriminator

    def __save_image_result(self, epoch):
        """Generates and stores the resulting image at the specified epoch.

        Args:
            epoch (int): The epoch the training is currently at.
        """
        _fig, a = plt.subplots(3,3, figsize=(10,10))
        noise = tf.random.normal(shape=[9, self.codings_size])
        images = self.generator(noise)
        for i in range(len(images)):
            a[i//3][i%3].set_xticks([])
            a[i//3][i%3].set_yticks([])
            a[i//3][i%3].imshow(images[i], cmap='gray')
        plt.savefig(self.result_dir + 'image_at_epoch_{epoch}.png'.format(epoch=epoch))

    def __create_batched_dataset(self, dataset, batch_size):
        """Create a batched dataset from the input dataset.

        Args:
            dataset (numpy.ndarray): The images dataset.
            batch_size (int): The size of each batch which the dataset would be divided into.

        Returns:
            [PrefetchDataset]: The dataset that has been divided into batches.
        """
        batched_dataset = tf.data.Dataset.from_tensor_slices(dataset).shuffle(buffer_size=1000)
        batched_dataset = batched_dataset.batch(batch_size, drop_remainder=True).prefetch(1)
        return batched_dataset

    def train(self, batch_size, epochs, dataset):
        # Create a batched dataset
        batched_dataset = self.__create_batched_dataset(dataset, batch_size)

        # Grab the separate components
        generator, discriminator = self.model.layers

        # For every epcoh
        for epoch in range(epochs):
            print(f"Currently on Epoch {epoch+1}")
            i = 0
            # For every batch in the dataset
            for X_batch in batched_dataset:
                i=i+1
                if i%20 == 0:
                    print(f"\tCurrently on batch number {i} of {len(dataset)//batch_size}")

                #####################################
                ## TRAINING THE DISCRIMINATOR ######
                ###################################
                # Create Noise
                noise = tf.random.normal(shape=[batch_size, self.codings_size])
                # Generate numbers based just on noise input
                gen_images = generator(noise)
                # Concatenate Generated Images against the Real Ones
                X_fake_vs_real = tf.concat([gen_images, tf.dtypes.cast(X_batch,tf.float32)], axis=0)
                # Targets set to zero for fake images and 1 for real images
                y1 = tf.constant([[0.]] * batch_size + [[1.]] * batch_size)
                # This gets rid of a Keras warning
                discriminator.trainable = True
                # Train the discriminator on this batch
                discriminator.train_on_batch(X_fake_vs_real, y1)
                
                
                #####################################
                ## TRAINING THE GENERATOR     ######
                ###################################
                # Create some noise
                noise = tf.random.normal(shape=[batch_size, self.codings_size])
                # We want discriminator to belive that fake images are real
                y2 = tf.constant([[1.]] * batch_size)
                # Avoid a warning
                discriminator.trainable = False
                # Train the generator on this batch
                self.model.train_on_batch(noise, y2)

                # Update the generator and discriminator of the model instance
                self.generator = generator
                self.discriminator = discriminator
                
            # Store the resulting image every 5 epochs
            if (epoch+1)%5 == 0:
                self.__save_image_result(epoch+1)
                
        print("TRAINING COMPLETE")            