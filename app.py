from flask import Flask, request,jsonify
import numpy as np
from PIL import Image 
from io import BytesIO
import tensorflow as tf
from tensorflow.keras import backend as K
from tensorflow.keras.layers import Dot
from tensorflow.keras.models import load_model
import firestore_funcs as ff
from flask_cors import CORS
import base64
import json

def cosine_similarity(vects):
  x, y = vects
  dotxy = Dot(axes=1)([x, y])
  magx  = K.sqrt(Dot(axes=1)([x,x]))
  magy  = K.sqrt(Dot(axes=1)([y,y]))
  return (dotxy/(magx*magy))

app = Flask(__name__)
CORS(app)

# models are in the shared drive
model1 = load_model('models//vgg_model_new.h5', compile = False)
print("vgg model loaded")
model2 = load_model('models//resnet_model_new.h5', compile = False)
print("resnet model loaded")
model3 = load_model('models//efficientnet_model_new.h5', compile = False)
print("efficientnet model loaded")

@app.route("/", methods=["GET"])
def welcome():
    return "(☞ ಠ_ಠ)☞ _('catch that mouse! it has our flask app!')\n............................................…ᘛ⁐̤ᕐᐷ"

@app.route("/emb", methods=["GET","POST"])
def get_emb():
    print("emb")
    data=request.get_json()
    file = data['image']
    print("file loaded")
    img = Image.open(BytesIO(base64.b64decode(data['image'][22:])))
    print("opened image")
    img=img.resize((224,224))
    img=np.array(img)
    emb1=model1.predict([np.expand_dims(img,axis=0)])
    print("emb1:",len(emb1[0]))
    emb2=model2.predict([np.expand_dims(img,axis=0)])
    print("emb2:",len(emb2[0]))
    emb3=model3.predict([np.expand_dims(img,axis=0)])
    print("emb3:",len(emb3[0]))
    return {
        "message":'successful',
        "vgg_embedding":emb1[0].tolist(),
        "resnet_embedding":emb2[0].tolist(),
        "effnet_embedding":emb3[0].tolist()
    }
  
@app.route("/dbtest", methods=["GET"])
def db_test():
    return {
        "message":"successful",
        "vgg":ff.getDocNames('vgg')['names'],
        "resnet":ff.getDocNames('resnet')['names'],
        "effnet":ff.getDocNames('effnet')['names']
    }

@app.route("/predict", methods=["GET","POST"])
def predict_image():
    try:
        data=request.get_json()
        img = Image.open(BytesIO(base64.b64decode(data['image'][22:])))
        img=img.resize((224,224))
        img=np.array(img)
        emb1=model1.predict([np.expand_dims(img,axis=0)])
        emb2=model2.predict([np.expand_dims(img,axis=0)])
        emb3=model3.predict([np.expand_dims(img,axis=0)])
        print("embedding size:",len(emb1[0]))
        preds1 = []
        preds2 = []
        preds3 = []
        b = ff.getAvgArrays('vgg')
        if b['message']=='successful':
            for i in b['doc_arrays']:
                preds1.append(cosine_similarity([tf.constant(np.expand_dims(i['avgarray'],axis=0)),tf.constant(emb1)]).numpy()[0][0])
        b = ff.getAvgArrays('resnet')
        if b['message']=='successful':
            for i in b['doc_arrays']:
                preds2.append(cosine_similarity([tf.constant(np.expand_dims(i['avgarray'],axis=0)),tf.constant(emb2)]).numpy()[0][0])
        b = ff.getAvgArrays('effnet')
        if b['message']=='successful':
            for i in b['doc_arrays']:
                preds3.append(cosine_similarity([tf.constant(np.expand_dims(i['avgarray'],axis=0)),tf.constant(emb3)]).numpy()[0][0])
        
        preds = np.average(np.array([preds1,preds2,preds3]),axis=0).tolist()
        print("predicted array:",preds)
        m = max(preds)
        if m>0.85:
            print("predicted class and certainty:",b['doc_arrays'][preds.index(m)]['name'],m)
            return {
                "message":'successful',
                "class":b['doc_arrays'][preds.index(m)]['name'],
                "vgg_array":emb1[0].tolist(),
                "resnet_array":emb2[0].tolist(),
                "effnet_array":emb3[0].tolist()
                }
        else:
            return {
                "message":'This image did not match with any existing class',
                "vgg_array":emb1[0].tolist(),
                "resnet_array":emb2[0].tolist(),
                "effnet_array":emb3[0].tolist()
                }
    except:
        return {
            "message":"prediction error"
        }

@app.route("/samples", methods=["GET"])
def class_samples():
    try:
        name = request.args.get('class')
        return {
            "message":"successful",
            "vgg":ff.getDocSamples('vgg',name),
            "resnet":ff.getDocSamples('resnet',name),
            "effnet":ff.getDocSamples('effnet',name)
        }
    except:
        return {
            "message":"sampling error"
        }

@app.route("/insert", methods=["POST"])
def db_insert():
    try:
        body = request.get_json()
        name = body['class']
        vect1 = body['vgg_array']
        vect2 = body['resnet_array']
        vect3 = body['effnet_array']
        if len(vect1)==len(vect2)==len(vect3)==512:
            return {
                "message":"successful",
                "vgg":ff.insertDoc('vgg', name, vect1),
                "resnet":ff.insertDoc('resnet', name, vect2),
                "effnet":ff.insertDoc('effnet', name, vect3)
            }
        else:
            return {
                "message":"did not receive 3 arrays of length 512"
            }
    except:
        return {
            "message":"insertion error"
        }

@app.route("/deletesample", methods=["POST"])
def delete_recent():
    try:
        body = request.get_json()
        name = body['class']
        return {
            "message":"successful",
            "vgg":ff.deleteLatestDoc('vgg', name),
            "resnet":ff.deleteLatestDoc('resnet', name),
            "effnet":ff.deleteLatestDoc('effnet', name)
        }
    except:
        return {
            "message":"deletion error"
        }

if __name__ == '__main__':
    app.run()
