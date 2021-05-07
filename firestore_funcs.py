import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred1 = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred1)

db=firestore.client()
print("database connected")

#getting array average
def arr_avg(arr1, arr2, n):
    for i in range(len(arr1)):
        arr1[i] = (n*arr1[i] + arr2[i])/(n+1)
    return arr1

#undo array average
def undo_avg(arr1, arr2, n):
    if n!= 1:
        for i in range(len(arr1)):
            arr1[i] = (n*arr1[i] - arr2[i])/(n-1)
        return arr1
    else:
        return arr1

#getting existing document names
def getDocNames(model_name):
    try:
        docnames = db.collection(model_name).document('#metadata').get().to_dict()
        return {
            'message':'successful',
            'model':model_name,
            'names': sorted(docnames['classes']),
            'nos': docnames['nos']
        }
    except:
        return {
            "message":model_name+" database error"
        }

#inserting new document
def insertDoc(model_name, name, vect):
    try:
        data = {
            'array':vect,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        docsname = name+'_docs'
        if name in getDocNames(model_name)['names']:
            docref = db.collection(model_name).document(name)
            docdict = docref.get().to_dict()
            docref.collection(docsname).add(data)
            newarr = arr_avg(docdict['avgarray'], vect, docdict['samples'])
            docref.update({"samples": firestore.Increment(1), "avgarray":newarr})
            return {
                "message":"successfully inserted document into class "+name+" into "+model_name+" DB"
            }
        else:
            db.collection(model_name).document('#metadata').update({'nos':firestore.Increment(1), 'classes':firestore.ArrayUnion([name])})
            db.collection(model_name).document(name).set({"name": name,"avgarray": vect,"samples": 1})
            db.collection(model_name).document(name).collection(docsname).add(data)
            return {
                "message":"successfully created new class "+name+" and inserted document into "+model_name+" DB"
            }
    except:
        return {
            "message":model_name+" database error"
        }

#getting document template arrays from each class
def getAvgArrays(model_name):
    try:
        docs = db.collection(model_name).where("name", "!=", model_name).get()
        docarr = []
        if len(docs)>0:
            for i in docs:
                ii = i.to_dict()
                docarr.append({'name':ii['name'], 'avgarray':ii['avgarray']})
            return {
                "message":'successful',
                "model":model_name,
                "doc_arrays":docarr
            }
        else:
            return {
                "message":'no documents in the '+model_name+' DB'
            }
    except:
        return {
            "message":model_name+" database error"
        }

#get all the documents of a class
def getDocSamples(model_name, name):
    try:
        docs = [] 
        if name in getDocNames(model_name)['names']:
            docsname = name+'_docs'
            res = db.collection(model_name).document(name).collection(docsname).order_by('timestamp').get()
            for i in res:
                docs.append(i.to_dict())
            return {
                'message':'successful',
                'model':model_name,
                'docs':docs
            }
        else:
            return {
                'message': "class "+name+" doesn't exist in the "+model_name+" DB"
            }
    except:
        return {
            "message":model_name+" database error"
        }

#deleting latest document
def deleteLatestDoc(model_name, name):
    try:
        if name in getDocNames(model_name)['names']:
            docsname = name+'_docs'
            res = db.collection(model_name).document(name).collection(docsname).order_by('timestamp').get()
            key = res[-1].id
            arr1 = db.collection(model_name).document(name).get().to_dict()['avgarray']
            n = db.collection(model_name).document(name).get().to_dict()['samples']
            arr2 = db.collection(model_name).document(name).collection(docsname).document(key).get().to_dict()['array']
            arr1 = undo_avg(arr1, arr2, n)
            db.collection(model_name).document(name).collection(docsname).document(key).delete()
            db.collection(model_name).document(name).update({"samples": firestore.Increment(-1), "avgarray":arr1})
            if n == 1:
                db.collection(model_name).document(name).delete()
                db.collection(model_name).document('#metadata').update({"classes": firestore.ArrayRemove([name]),"nos": firestore.Increment(-1)})
            return {
                'message': "successfully deleted latest document in the "+model_name+" DB"
            }
        else:
            return {
                'message': "class "+name+" doesn't exist in the "+model_name+" DB. Cannot delete"
            }
    except:
        return {
            "message":model_name+" database error"
        }
