# Implement the SSIM metric for comparing two images
# Read both image files
import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# SSIM meaning
# 1 is perfect similarity
# 0 is no similarity

# TODO:: Generate 100 images from each of the following:
# generated from pix2pix, generated from CycleGAN, and one ground truth from the test set
# TODO:: Implement the sliding window/ average SSIM metric
# TODO:: plot/display results for 100 images
# CycleGAN trained on unpaired data sets

def ssim_score(image_real_out_path, 
               image_fake_out_path, 
               WINDOW_SIZE=(11, 11),
               SLIDE_X=0, SLIDE_Y=0,   #top-left corner of the window (pixel loc on overall image)
               L_chosen=255, k_1_chosen=0.01, k_2_chosen=0.03, 
               ALPHA_chosen=1, BETA_chosen=1, GAMMA_chosen=1, # emphasis of Luminance, Contrast, Structure
               plotOn=False,
               printData=False,
               image_number="WHICH IMAGE?", # fill out this if plot on
               generation_type='PIX or CYC?'): # fill out this if plot on
    
    # Read the images
    image_real_out = cv2.imread(image_real_out_path)
    image_fake_out = cv2.imread(image_fake_out_path)

    # start out using grayscale images
    image_real_out_gray = cv2.cvtColor(image_real_out, cv2.COLOR_BGR2GRAY)
    image_fake_out_gray = cv2.cvtColor(image_fake_out, cv2.COLOR_BGR2GRAY)

    # Window size
    image_size = (image_real_out.shape[0], image_real_out.shape[1])
    window_size = WINDOW_SIZE # (11, 11) is what the people are saying

    slide_x = SLIDE_X
    slide_y = SLIDE_Y

    window_real = image_real_out_gray[slide_x:slide_x + window_size[0], slide_y: slide_y + window_size[1]]
    window_fake = image_fake_out_gray[slide_x:slide_x + window_size[0], slide_y: slide_y + window_size[1]]

    # mu_real is the pixel sample mean of image_real_out_grey
    mu_real = window_real.mean()
    mu_fake = window_fake.mean()

    # compute variances
    sigma_squared_real = window_real.var()
    sigma_squared_fake = window_fake.var()

    # compute covariance
    covariance = np.cov(window_real.flatten(), window_fake.flatten())[0][1]

    # L is the dynamic range of the pixel values
    L = L_chosen #255
    k_1 = k_1_chosen #0.01
    k_2 = k_2_chosen #0.03

    # computing c_1 and c_2
    c_1 = (k_1 * L) ** 2
    c_2 = (k_2 * L) ** 2
    c_3 = c_2 / 2

    luminance = (2 * mu_real * mu_fake + c_1) / (mu_real ** 2 + mu_fake ** 2 + c_1)
    contrast = (2 * np.sqrt(sigma_squared_real) * np.sqrt(sigma_squared_fake) + c_2) / (sigma_squared_real + sigma_squared_fake + c_2)
    structure = (covariance + c_3) / (np.sqrt(sigma_squared_real) * np.sqrt(sigma_squared_fake) + c_3)

    ALPHA = ALPHA_chosen #1
    BETA = BETA_chosen #1
    GAMMA = GAMMA_chosen #1

    ssim = luminance ** ALPHA * contrast ** BETA * structure ** GAMMA

    if plotOn==True:
        # Plot the images side by side
        plt.subplot(1, 2, 1)
        plt.imshow(window_real, cmap='gray')
        plt.title(f'Real | Image No. {image_number} ')
        plt.subplot(1, 2, 2)
        plt.imshow(window_fake, cmap='gray')
        plt.title(f'Fake | {generation_type}')

        # add to the plot the SSIM value along with the luminance, contrast, and structure values
        plt.suptitle('SSIM: %.2f, Luminance: %.2f, Contrast: %.2f, Structure: %.2f' % (ssim, luminance, contrast, structure))

        plt.show()
    if printData==True:
        print(f'Image#{image_number}-{generation_type} ~ SSIM: {ssim:.2f}, Luminance: {luminance:.2f}, Contrast: {contrast:.2f}, Structure: {structure:.2f}')

    return ssim, luminance, contrast, structure

#### HOW TO USE ##################################################

# Three images are real_pair (real_in, real_out) and fake_out
image_real_out_path = 'data/frame_0_real.png'
image_fake_out_path = 'data/frame_0_fake.png'

ssim, luminance, contrast, structure = ssim_score(image_real_out_path, image_fake_out_path, plotOn=True)

####################################################################################################
####################################################################################################


## TODO:: NEED TO INCLUDE FUNCTIONALITY ABOUT THE WINDOW SLIDING AND AVERAGING

def evaluate_folder_ssim(folder_path, 
                    WINDOW_SIZE=(11,11),
                    ALPHA_chosen=1,BETA_chosen=1, GAMMA_chosen=1,
                    STRIDE_X=1, STRIDE_Y=1,   # stride of window 
                    plotAll=False,
                    plotSpecial=False,
                    plotScores=False,
                    printData=False):

    #### Designate Image Source

    # find all images with a name containing 'real'
    real_images = [fileName for fileName in os.listdir(folder_path) if 'real' in fileName]
    real_images.sort()

    # find all images with a name containing 'cycle'
    cycle_images = [fileName for fileName in os.listdir(folder_path) if 'cycle' in fileName]
    cycle_images.sort()

    # find all images with a name containing 'pix2pix'
    pix2pix_images = [fileName for fileName in os.listdir(folder_path) if 'pix2pix' in fileName]
    pix2pix_images.sort()

    # find all images with a name containing 'ground_truth'
    ground_truth_images = [fileName for fileName in os.listdir(folder_path) if 'ground_truth' in fileName]
    ground_truth_images.sort()

    ##### Get the SSIM scores for each image
    ssim_scores_pix2pix = []
    ssim_scores_cycle = []
    
    for i in range(len(real_images)):
        image_number = real_images[i].split('_')[0]

        ssim_scores_pix2pix_this_image = []
        ssim_scores_cycle_this_image = []

        slide_X = 0
        while slide_X + WINDOW_SIZE[0] < 256:
            slide_Y = 0
            while slide_Y + WINDOW_SIZE[1] < 256:
                ssim_scores_pix2pix_this_image.append(ssim_score(os.path.join(folder_path, real_images[i]), 
                                                    os.path.join(folder_path, pix2pix_images[i]),
                                                    WINDOW_SIZE=WINDOW_SIZE,
                                                    SLIDE_X=slide_X, SLIDE_Y=slide_Y,
                                                    ALPHA_chosen=ALPHA_chosen, BETA_chosen=BETA_chosen, GAMMA_chosen=GAMMA_chosen,
                                                    plotOn=plotAll,
                                                    printData=printData,
                                                    image_number=image_number,
                                                    generation_type='PIX')[0])
                ssim_scores_cycle_this_image.append(ssim_score(os.path.join(folder_path, real_images[i]),
                                                    os.path.join(folder_path, cycle_images[i]),
                                                    WINDOW_SIZE=WINDOW_SIZE,
                                                    SLIDE_X=slide_X, SLIDE_Y=slide_Y,
                                                    ALPHA_chosen=ALPHA_chosen, BETA_chosen=BETA_chosen, GAMMA_chosen=GAMMA_chosen,
                                                    plotOn=plotAll,
                                                    printData=printData,
                                                    image_number=image_number,
                                                    generation_type='CYC')[0])
                slide_Y += STRIDE_X
            slide_X += STRIDE_Y

        if plotSpecial==True:
            # make the figure large
            plt.figure(figsize=(20, 5))
            plt.subplot(1,4,1)
            plt.imshow(cv2.imread(os.path.join(folder_path, real_images[i])))
            plt.title('Original X')
            plt.xticks([]), plt.yticks([])

            plt.subplot(1,4,2)
            plt.imshow(cv2.imread(os.path.join(folder_path, ground_truth_images[i])))
            plt.title('True Y')
            plt.xticks([]), plt.yticks([])

            plt.subplot(1,4,3)
            plt.imshow(cv2.imread(os.path.join(folder_path, cycle_images[i])))
            plt.title('CycleGAN Y')
            plt.xticks([]), plt.yticks([])
            plt.xlabel(f"SSIM = {np.mean(ssim_scores_cycle_this_image):.2f}")

            plt.subplot(1,4,4)
            plt.imshow(cv2.imread(os.path.join(folder_path, pix2pix_images[i])))
            plt.title('pix2pix Y')
            plt.xticks([]), plt.yticks([])
            plt.xlabel(f"SSIM = {np.mean(ssim_scores_pix2pix_this_image):.2f}")

            plt.suptitle(f"Image No. {image_number}")
            plt.show()
            

        ssim_scores_pix2pix.append(np.mean(ssim_scores_pix2pix_this_image))
        ssim_scores_cycle.append(np.mean(ssim_scores_cycle_this_image))

        
    if plotScores==True:
        plt.scatter(range(len(ssim_scores_pix2pix)), ssim_scores_pix2pix, label='pix2pix')
        plt.scatter(range(len(ssim_scores_cycle)), ssim_scores_cycle, label='CycleGAN')
        plt.legend()
        plt.xlabel('Example Index')
        plt.ylabel('SSIM Score')
        plt.show()
        # print Cycle beats Pix2Pix in X% of the cases
        print(f'CycleGAN beats pix2pix in {np.sum(np.array(ssim_scores_cycle) > np.array(ssim_scores_pix2pix))/len(ssim_scores_pix2pix)*100}% of cases')

        
    return ssim_scores_pix2pix, ssim_scores_cycle

#### HOW TO USE ##################################################

#folder_path = 'cycle_pix_maps_compared'

#ssim_scores_pix2pix, ssim_scores_cycle = evaluate_folder_ssim(folder_path, plotScores=True)


