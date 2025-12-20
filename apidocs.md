# Inference

| Endpoint | [https://sinkin.ai/api/inference](https://sinkin.ai/inference) |
| --- | --- |
| Request Type | **POST** request |
| Input | **`access_token`**: String, **required**

**`model_id`**: String, **required,** [see how to get the id of a model](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21) 

**`prompt`**: String, **required

`version`**: String, optional
Model version, default to the latest version

**`width`**: Int, optional
default = `512`, must be increment of 8
valid range is 128 to 896
commonly used values: 512, 640, 768

**`height`**: Int, optional
default = `768`, must be increment of 8
valid range is 128 to 896
commonly used values: 512, 640, 768

**`negative_prompt`**: String, optional
**`use_default_neg`**: String, optional
Append the default negative prompt or not
pass in `“true”` or `“false”`, default = `“true”` 

**`steps`**: Int, optional
Number of inference steps
default = `30` valid range is 1 to 50

**`scale`**: Float, optional
Guidance scale
default = `7.5` or model's default scale if one is set
valid range is 1 to 20

**`num_images`**: Int, optional, default = `4`
**`seed`**: Int, optional, default = `-1`
**`scheduler`**: String, optional, default = `”DPMSolverMultistep”` or model’s default scheduler if one is set, [see options](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21)

**`lora`**: String, optional
id of the LoRA model. You can query [/models](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21) to get the full list of LoRA
**`lora_scale`**: Float, optional, default = `0.75` |
| Extra input for img2img | **`init_image_file`**: a file object, the base image, **required** for img2img

**`image_strength`**:  Float, optional
How much to transform the base image, default = `0.75`

**`controlnet`**: String, optional
ControlNet to use, legit values are `canny`, `depth` and `openpose`
Note when `controlnet` is set, `image_strength` will have no effect

see [one example of how to make img2img request](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21)
 |
| Output | **Success**: 
`{ 
    error_code: 0, 
    images=[ ‘image url’, ‘image url’, …] ,
    credit_cost: 2.2,
    inf_id: 'xxxxxxxxxxxxxx'
}`

**Failure**:
 `{ error_code: 1, message: “This is an error message” }` |

### Model ID

You can call **[`/models`](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21)** to get the complete model list, including image models, LoRAs and video models. The id of each model can be found in the returned json. 

You can also go to [sinkin.ai](http://sinkin.ai), enter a model page and the last part of the url is the model id. E.g. for the model at https://sinkin.ai/m/vlDnKP6, the model id is `vlDnKP6`.

**The ids of some commonly used models:**

| Model Name | Model ID |
| --- | --- |
| majicMIX realistic | yBG2r9O |
| AbsoluteReality | mGYMaD5 |
| DreamShaper | 4zdwGOB |
| MeinaHentai | RR6lMmw |
| Realistic Vision | r2La2w2 |
| Babes | mG9Pvko |
| RealCartoon3D | gLv9zeq |
| NeverEnding Dream | qGdxrYG |
| Hassaku | 76EmEaz |
| Deliberate | K6KkkKl |
| MeinaMix | vln8Nwr |

### Scheduler Options

| DPMSolverMultistep |
| --- |
| K_EULER_ANCESTRAL |
| DDIM |
| K_EULER |
| PNDM |
| KLMS |

### An example of how to make an img2img request in python

```python
    params = {
        'access_token': 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
        'model_id': 'xxxxx',
        'prompt': 'an angry orc looking at camera smiling',
        'num_images': 1,
        'scale': 7,
        'steps': 30,
        'width': 512,
        'height': 768,
        # 'image_strength': 0.75,
        # 'controlnet': 'openpose'
    }

    files = {'init_image_file': open('path-to-image-file', 'rb')}
    
    r = requests.post('https://sinkin.ai/api/inference', files=files, data=params)

    print(r.text)
```

# Models

Get all available image models, LoRAs and video models

| Endpoint | https://sinkin.ai/api/models |
| --- | --- |
| Request Type | **POST** request |
| Input | **`access_token`**: String, **required** |
| Output | **Success**: 
`{ 
    error_code: 0, 
    models: [ {'id': 'XXXX', 'title': 'XXXX', 'cover_img': 'xxxxxxxx', 'link': 'xxxxxxx'}, ... ] ,
    loras: [ {'id': 'XXXX', 'title': 'XXXX', 'cover_img': 'xxxxxxxx', 'link': 'xxxxxxx'}, ... ] ,
    video_models: [ {'id': ..., 'title': ..., ... }]
}`

**Failure**:
 `{ error_code: 1, message: “This is an error message” }` |

# Upscale

Upscale an image

| Endpoint | [https://sinkin.ai/api/upscale](https://sinkin.ai/api/models) |
| --- | --- |
| Request Type | **POST** request |
| Input | **`access_token`**: String, **required

`inf_id`**: String, **required**
The id of the inference where the image was generated. This is in the returned json of `/api/inference`

**`url`**: String, **required**
The url of the image to be upscaled

**`type`**: String, optional
Upscale type
Valid types: **`esrgan`** or **`hires_fix`**, default is **`esrgan`**

**`scale`**: Float, optional
How much to upscale, valid range is between 2 and 4, only applicable when type is **`esrgan`**, default is 2

**`strength`**: Float, optional
How strong the hires fix is, valid range is between 0 and 1, only applicable when type is **`hires_fix`**, default is 0.6 |
| Output | **Success**: 
`{
  "credit_cost": 6.0,
  "error_code": 0,
  "output": "image_url"
}`

**Failure**:
 `{ error_code: 1, message: “This is an error message” }` |

# Video

Text to video or image to video generation

| Endpoint | [https://sinkin.ai/api/](https://sinkin.ai/api/models)video |
| --- | --- |
| Request Type | **POST** request |
| Input | **`access_token`**: String, **required

`model_id`**: String, **required,** [see how to get the id of a model](https://www.notion.so/SinkIn-API-7fa0dc746d624629bb3c680d913cbbf4?pvs=21) 

**`prompt`**: String, **required

`image_url`**: String, **required for image to video models

`resolution`**: String, optional
’480p’ or ‘720p’. Default to ‘480p’

**`fps` :** Int, optional
Frames per second. Default to 16. |
| Output | **Success**: 
`{
  "credit_cost": 12.0,
  "error_code": 0,
  "video_url": "video_url"
  "inf_id": 'xxxxxxxxxxxxxx'
}`

**Failure**:
 `{ error_code: 1, message: “This is an error message” }` |