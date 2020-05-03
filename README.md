# leveeNet: Deep learning based levee detection from space  
Preliminary version   
## Project description  
trying to detect two things:  
- **where** does levees locate at?  
- **what** are the properties (e.g., height) of those levees?  
  
As of 2020/04, currently am working in the first bullet, **where** are levees.  
  
## Change log  
2020/05/02 added U-Net for image segmentation.  
2020/04/29 XGBoost (Acc=96%, Precision=0.95, Recall=0.98); CNN (Acc=86%, Precision=0.79, recall=0.96).  
2020/04/26 started project. created repository.  
  
## Source trees  
- **gee**: scripts for processing in/out-of Google Earth Engine  
- **preprocess**: scripts for preprocessing output images from gee  
- **model**: xgboost, cnn, and unet. for additional preprocessing, model definitions, and training/testing models.  
  
## Workflow  
### Google Earth Engine processing  
To generate images to train a model, process satellite-images on Google Earth Engine.  
The dataset currently used:  
- [Sentinel-2 MSI: MultiSpectral Instrument, Level-2A](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
- [NLCD: USGS National Land Cover Database](https://developers.google.com/earth-engine/datasets/catalog/USGS_NLCD)
- [USGS National Elevation Dataset 1/3 arc-second](https://developers.google.com/earth-engine/datasets/catalog/USGS_NED)
- [National Levee Database](https://levees.sec.usace.army.mil/#/) by USACE  
- [WWF HydroSHEDS Free Flowing Rivers Network v1](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_v1_FreeFlowingRivers)  
  
The images are generated by following steps:  
1. locate levees (from National Levee Database) on the map.  
2. locate hydrography (rivers) on the map.  
3. from single river centerline at a cross-section (line perpendicular to the centerline), draw a buffered-circle and its bounded rectangle. This bounded rectangle is the bbox of output image.  
4. map all other datasets and aggregate them into one image with multuiple bands.  
   - For Sentinel-2, images from 2019-01-01 to 2020-03-31 was processed with cloud masks, and took a median of cloud-free images where available.  
5. clip the image with the bboxes, and output as a GeoTIFF file.  

As this process analyzes millions of satellite-images, the downloading process takes long time. We can potentially have thousands of images by this process, but for this reason as of 2020/04 I limited the number of processed regions by basin and stream order (resulted in 1.5K images).  
  
### Image preprocessing  
After downloading GeoTIFF files, preprocess data to perform standardization and create labels for Keras-ready format.  
While Keras has some utilities for preprocessing, as we have multiple bands different from normal images we need to do this by outselves.  
1. standardization 
   - elevation: *sampleWiseStandardization*. We are more interested in the variation of the elevation in a image, not an entire dataset. 
     - For instance, there should be differences in mean elevation between images from mountain and near-ocean, but this difference of mean may not be relavent.   
   - bands from Sentinel-2: *featureWiseStandardization*. they are more like global variables, thus perform standardiztion for an entire dataset.  
2. one-hot-encoding
   - as the land cover band (channel) is categorical, create dummy variables via one-hot-encoding. 
   - We also need to remove homogeneous layers (i.e., all-zero).  
3. labeling: make labels from the levee layer.  
4. output to netCDF4 to read it later via XArray.  
   
### Model development  
#### CNN: image-wise classification
The model design is still underway, but the current architecture is based on three building blocks, two averageMaxPooling, one globalAveragePooling, two fully conntected layers. See `model/cnn/model.py` for the actual architecture. Before passing the images to the model, following additional preprocess was performed:
   - 2D Maximum pooling to reduce image size (kernel_size=4), and nearest interpolation to get 256x256px images.
   - image augmentation via Affine conversion. performed probabilistically when a batch is created.  
  
#### XGBoost: image-wise classification  
Along with the CNN, the model using XGBoost was also included. The hyperparameters are tuned by GridSearchCV. Before passing the images to the model, following additional preprocess was performed:  
   - reduce 2D (height x width) dimension into 1D.  
     - Sentinel bands [R, G, B, NIR, SWIR]: mean
     - land cover (one-hot-encoded): sum
     - elevation: std
   - after the reduction of images, I applied feature-wise standardization  
  
#### U-Net: pixel-wise image segmentation  
Being different from the models above, this model is meant for pixel-wise levee detection, or image segmentation. The architecture is following to the original paper ([Ronneberger et al., 2015](https://arxiv.org/abs/1505.04597)), but with batch normalization after ReLu activation. This architecture has VAE-style (encoder/decoder) image generation process, with skip connections at each convolution level. See `model/unet/model.py` for the actual implementation. The preprocessing part is similar to the CNN above, with slight modifications:  
   - 2D Maximum pooling to reduce image size (kernel_size=2), and nearest interpolation to get 512x512px images.  
   - image augmentation via Affine conversion. performed probabilistically.  
   - labels are now 2D images, with 0: non-levee 1: with-levee pixels.
  
#### PSP-Net: pixel-wise image segmentation  
*will be considered in the future work*  
  
### Train and test the model  
The scripts are tested in the following configurations:
   - NVIDIA GTX-1070, CUDA10.1, CuDNN7, and Tensorflow-2.1.  
   - NVIDIA Tesla P100, CUDA10.1, CuDNN7, and Tensorflow-2.1  
  
The scripts should work under this configuration. While other configuration may also work, you will need corresponding CUDA, CuDNN, and Tensorflow version to run the scripts.  
To replicate the environment, Dockerfile is in this repository.  
  
To train the cnn model under model/cnn/:  
```bash  
python train.py -c ${configFile.ini}
```
  
The tensorboard callback is passed to the model. To show tensorboard:  
```bash
tensorboard --logDir ${log_directory}
```
  
To see tensorboard running in the container, bind the ports when you run docker:  
```bash
docker build .
docker run -it --name ${container_name} -v ${path_to_leveeNet}/leveeNet:/opt/analysis/leveeNet -p 9088:9088
tensorboard --logDir ${log_directory} --port 9088 --bind_all
```
  

## Future improvements  
- some of the feature engineering (e.g., elevation) can be improved.  
- use truely global dataset
- predict the location of levees in pixels via VAE  
- use [MERIT-HYDRO](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019WR024873)/[GRWL](https://science.sciencemag.org/content/361/6402/585) 
