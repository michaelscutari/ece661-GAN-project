import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
from PIL import Image
import torchvision.utils as vutils  # For image logging
import wandb  # Import Weights & Biases
import time

# custom classes
from model import GeneratorUNet, DiscriminatorPatchGAN
from dataset import Pix2PixDataset
from config import Config

# Device
device = torch.device('cuda')

# Initialize Weights & Biases
wandb.init(
    project="pix2pix-map2sat",
    config={
        "learning_rate": Config.learning_rate,
        "beta1": Config.beta1,
        "beta2": Config.beta2,
        "batch_size": Config.batch_size,
        "num_epochs": Config.num_epochs,
        "lambda_L1": Config.lambda_L1,
    },
    name=Config.run_name,
    save_code=False
)

config = wandb.config

# Create necessary directories
os.makedirs(Config.checkpoint_dir, exist_ok=True)


# Dataset and DataLoader
train_dataset = Pix2PixDataset(
    input_dir=Config.train_input_dir,
    target_dir=Config.train_target_dir,
    transform=Config.data_transforms
)

train_loader = DataLoader(
    dataset=train_dataset,
    batch_size=Config.batch_size,
    shuffle=True,
    num_workers=4,
    drop_last=True
)

# Initialize models
generator = GeneratorUNet().to(device)
discriminator = DiscriminatorPatchGAN().to(device)

# Denormalize!
def denormalize(tensor):
    return tensor * 0.5 + 0.5

# Initialize weights
def initialize_weights(model):
    for m in model.modules():
        if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
            if m.weight is not None:
                nn.init.normal_(m.weight, 0.0, 0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, (nn.InstanceNorm2d)):
            if m.weight is not None:
                nn.init.normal_(m.weight, 1.0, 0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

initialize_weights(generator)
initialize_weights(discriminator)

# Loss functions
criterion_GAN = nn.BCEWithLogitsLoss().to(device)
criterion_L1 = nn.L1Loss().to(device)

# Optimizers
optimizer_G = optim.Adam(generator.parameters(), lr=Config.learning_rate, betas=(Config.beta1, Config.beta2))
optimizer_D = optim.Adam(discriminator.parameters(), lr=Config.learning_rate, betas=(Config.beta1, Config.beta2))

# Learning rate schedulers
lr_scheduler_G = optim.lr_scheduler.LambdaLR(optimizer_G, lr_lambda=lambda epoch: 1 - epoch / Config.num_epochs)
lr_scheduler_D = optim.lr_scheduler.LambdaLR(optimizer_D, lr_lambda=lambda epoch: 1 - epoch / Config.num_epochs)

# Select a fixed sample for consistent monitoring
fixed_sample = train_dataset[0]  # Change the index to select a different sample
fixed_input = fixed_sample['input'].unsqueeze(0).to(device)  # Add batch dimension
fixed_target = fixed_sample['target'].unsqueeze(0).to(device)  # Add batch dimension

input_images = denormalize(fixed_input.cpu())
target_images = denormalize(fixed_target.cpu())

img_grid_input = vutils.make_grid(input_images, normalize=False)
img_grid_target = vutils.make_grid(target_images, normalize=False)

wandb.log({
            'Input Images': [wandb.Image(img_grid_input, caption="Input")],
            'Target Images': [wandb.Image(img_grid_target, caption="Target")],
        })

# DEBUG
print("Starting training...")

# timing
training_start_time = time.time()

# Training loop
for epoch in range(1, Config.num_epochs + 1):
    
    generator.train()
    discriminator.train()

    # Timing

    epoch_start_time = time.time()
    epoch_batch_times = []

    for batch_idx, batch in enumerate(train_loader):
        batch_start_time = time.time()

        # Get input and target images
        input_image = batch['input'].to(device)
        target_image = batch['target'].to(device)

        # Labels for real and fake images
        real_label = torch.ones((input_image.size(0), 1, 30, 30), device=device)
        fake_label = torch.zeros((input_image.size(0), 1, 30, 30), device=device)

        # ---------------------
        #  Train Generator
        # ---------------------
        optimizer_G.zero_grad()

        # Generate images
        fake_image = generator(input_image)

        # Discriminator evaluates the fake images
        pred_fake = discriminator(input_image, fake_image)

        # Generator adversarial loss
        loss_GAN = criterion_GAN(pred_fake, real_label)

        # L1 loss
        loss_L1 = criterion_L1(fake_image, target_image) * Config.lambda_L1

        # Total generator loss
        loss_G = loss_GAN + loss_L1
        loss_G.backward()

        torch.nn.utils.clip_grad_norm_(generator.parameters(), max_norm=1.0)

        optimizer_G.step()
        

        # ---------------------
        #  Train Discriminator
        # ---------------------
        optimizer_D.zero_grad()

        # Real images
        pred_real = discriminator(input_image, target_image)
        loss_D_real = criterion_GAN(pred_real, real_label)

        # Fake images (detach to avoid training generator on these gradients)
        pred_fake = discriminator(input_image, fake_image.detach())
        loss_D_fake = criterion_GAN(pred_fake, fake_label)

        # Total discriminator loss
        loss_D = (loss_D_real + loss_D_fake) * 0.5
        loss_D.backward()

        torch.nn.utils.clip_grad_norm_(discriminator.parameters(), max_norm=1.0)

        optimizer_D.step()

        # ---------------------
        #  Logging
        # ---------------------

        batch_end_time = time.time()
        batch_time = batch_end_time - batch_start_time
        epoch_batch_times.append(batch_time)

        batches_done = epoch * len(train_loader) + batch_idx  # total number of batches processed so far
        if batches_done % 500 == 0:
            # DEBUG
            print(f"Logging! Total batches: {batches_done}", flush=True)
            # Log scalar metrics
            wandb.log({
                'Loss/Generator_GAN': loss_GAN.item(),
                'Loss/Generator_L1': loss_L1.item(),
                'Loss/Generator_Total': loss_G.item(),
                'Loss/Discriminator': loss_D.item(),
                'Learning Rate/Generator': optimizer_G.param_groups[0]['lr'],
                'Learning Rate/Discriminator': optimizer_D.param_groups[0]['lr'],
                'step': batches_done,
                'Epoch': epoch,
                'Batch': batch_idx,
                'Batch_time': batch_time
            })

    # ---------------------
    #  Logging
    # ---------------------

    # timing
    epoch_time = time.time() - epoch_start_time
    average_batch_time = sum(epoch_batch_times) / len(epoch_batch_times)

    # estimated time remaining
    remaining_epochs = Config.num_epochs - epoch
    estimated_remaining_time = remaining_epochs * epoch_time
    time_since_start = time.time() - training_start_time

    # Log epoch metrics and timing
    wandb.log({
        'Epoch': epoch,
        'Epoch_duration': epoch_time,
        'Average_batch_time': average_batch_time,
        'Estimated_remaining_time': estimated_remaining_time,
        'Time_since_start': time_since_start,
    })

    print(f"Epoch {epoch}/{Config.num_epochs} completed in {epoch_time:.2f}s. "
          f"Average batch time: {average_batch_time:.2f}s. "
          f"Estimated remaining time: {estimated_remaining_time/60:.2f} minutes."
          f"Time since start: {time_since_start/60:.2f} minutes", flush=True)

    # Log images
    with torch.no_grad():
        generator.eval()
        fake_sample = generator(fixed_input)

        output_images = denormalize(fake_sample.cpu())

        # Create image grids
        img_grid_fake = vutils.make_grid(output_images, normalize=False)

        # Log images to Weights & Biases
        wandb.log({
            'Input Images': [wandb.Image(img_grid_input, caption="Input")],
            'Target Images': [wandb.Image(img_grid_target, caption="Target")],
            'Fake Images': [wandb.Image(img_grid_fake, caption="Fake")]
        })

        generator.train()

    # Update learning rates
    lr_scheduler_G.step()
    lr_scheduler_D.step()

    # Save model checkpoints every 10 epochs
    if (epoch + 1) % 10 == 0:
        generator_path = os.path.join(Config.checkpoint_dir, f'generator_epoch_{epoch+1}.pth')
        discriminator_path = os.path.join(Config.checkpoint_dir, f'discriminator_epoch_{epoch+1}.pth')
        torch.save(generator.state_dict(), generator_path)
        torch.save(discriminator.state_dict(), discriminator_path)

        # Log model checkpoints to Weights & Biases as artifacts
        wandb.save(generator_path)
        wandb.save(discriminator_path)

# Finish the wandb run
wandb.finish()