import boto3
from datetime import date
from flask import Flask,request,jsonify,render_template,redirect,Response
from flask_cors import CORS
import mysql.connector  
import csv
app=Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/course',methods=['GET'])
def courseFunction():
    if request.method=='GET':
        s3 = boto3.resource('s3')
        BucketName="velusooryabucket"
        return createBucket(s3,BucketName)

@app.route('/upload',methods=['POST'])
def UploadFunction():
    if request.method=='POST':
        s3 = boto3.resource('s3')
        attendance=dict(request.form)
        print(attendance)
        course=''
        date=''
        year=''
        attendancelist=[]
        for val in attendance.keys():
            if(val=="course"):
                course=attendance[val]
            elif(val=="year"):
                year=attendance[val]
            elif(val=="date"):
                date=attendance[val]
            else:
                attendancelist.append([val,attendance[val]])
        filename=str(year)+'/'+str(date)+'.csv'
        filepath='temp.csv'
        with open(filepath, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(attendancelist)
        uploadFile(s3,course,filename,filepath)
        return {"success":"yeah"}

@app.route('/download',methods=['GET'])
def download():
    s3=boto3.resource('s3')
    bucketname=request.args.get("coursename")
    filename=request.args.get("filename")
    return downloadfile(s3,bucketname,filename)


@app.route('/restore',methods=['GET'])
def restoreobject():
    s3=boto3.resource('s3')
    objectname=request.args.get('objectname')
    bucketname=request.args.get('bucketname')
    object=s3.Object(bucketname,objectname)
    object.restore_object(
    
    RestoreRequest={
        'Days': 1,
        }
    )
    return {"sucess":objectname}
@app.route('/archive',methods=['GET'])
def archive():
    s3=boto3.resource('s3')
    objectname=request.args.get('objectname')
    bucketname=request.args.get('bucketname')
    object = s3.Object(bucketname,objectname)
    object.copy_from(CopySource =bucketname+"/"+objectname, StorageClass='GLACIER')
    return {"sucess":objectname}

    

@app.route('/bucketsList',methods=['GET'])
def ListBuckets():
    if request.method=='GET':
        s3=boto3.resource('s3')
        res=getBuckets(s3)
        return res


@app.route('/studentsList',methods=['GET'])
def ListStudents():
    if request.method=='GET':
        bucketname=request.args.get("course")
        year=request.args.get("year")
        res=getStudents(bucketname,year)
        return res


@app.route('/objects',methods=["GET"])
def getobjects():
    bucketname=request.args.get("course")
    year=request.args.get("year")
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)
    dic={}
    ind=0
    for key in bucket.objects.all() if year=='' else bucket.objects.filter(Prefix=str(year)+"/"):
        #print(key)
        metadata=s3.meta.client.head_object(Bucket=bucketname, Key=key.key)
        #print(metadata)
        print()
        print()
        storage_class=""
        if("StorageClass" in metadata):
            storage_class=metadata["StorageClass"]
        else:
            storage_class="STANDARD"
        restorestage="standard_storage_class"
        expirydate=""
        if(storage_class=="GLACIER"):
            if "x-amz-restore" not in metadata["ResponseMetadata"]["HTTPHeaders"]:
                restorestage="no_request_made"
            elif metadata["ResponseMetadata"]["HTTPHeaders"]["x-amz-restore"].split(',')[0].split('=')[1] == '"true"':
                print(metadata["ResponseMetadata"]["HTTPHeaders"]["x-amz-restore"].split(','))
                restorestage="restoring"
            else:
               
                expirydate=metadata["ResponseMetadata"]["HTTPHeaders"]["x-amz-restore"].split(',')[1]+metadata["ResponseMetadata"]["HTTPHeaders"]["x-amz-restore"].split(',')[2]
                restorestage="restored"
        dic[ind]={"objectname":key.key,"bucketname":key.bucket_name,"storageclass":storage_class,"restorestage":restorestage,"expirydate":expirydate}
        print(dic[ind])
        ind+=1
    return dic  
        




def createBucket(s3,bucketName):
    try:
        s3.create_bucket(Bucket=bucketName)
    except s3.meta.client.exceptions.BucketAlreadyExists as err:
        print("Bucket {} already exists!".format(err.response['Error']['BucketName']))





def uploadFile(s3,BucketName,FileName,filePath):
    s3.meta.client.upload_file(filePath,BucketName,FileName)




def downloadFile(s3,BucketName,FileName,filePath):
    try:
        s3.Object(BucketName, FileName).download_file(
        filePath)
    except:
        print("Error")



def getBuckets(s3):
    BucketsList=[]
    dic=dict()
    for bucket in s3.buckets.all():
        BucketsList.append(bucket.name)
    dic={"Buckets":BucketsList}
    return jsonify(dic)

def getStudents(coursename,year):
    studentsList=[]
    print(coursename,year)
    myconn = mysql.connector.connect(host = "localhost", user = "root",passwd = "",port=3308,database="students")   
    cur = myconn.cursor()
    query="select name from students where course=%s and year=%s"
    parameters=(coursename,year)
    cur.execute(query,parameters)  
    result = cur.fetchall()    
    for name in result:
        
        studentsList.append(name)
    myconn.close()  
    dic={"students":studentsList}
    return jsonify(dic)


def getObjects(s3,bucketname,year):
    bucket = s3.Bucket(bucketname)
    dic={}
    ind=0
    for key in bucket.objects.all() if year=='' else bucket.objects.filter(Prefix=str(year)+"/"):
        metadata=s3.meta.client.head_object(Bucket=bucketname, Key=key.key)
        storage_class=""
        if("StorageClass" in metadata):
            storage_class=metadata["StorageClass"]
        else:
            storage_class="STANDARD"
        dic[ind]={"objectname":key.key,"bucketname":key.bucket_name,"storageclass":storage_class}
        ind+=1
    return dic  




def downloadfile(s3,BucketName,FileName):
    
        file=s3.Bucket(BucketName).Object(FileName).get()
        return Response(
            file['Body'].read(),
            mimetype='text/plain',
            headers={"Content-Disposition":"attachment;filename={}".format(FileName)}
            )

if __name__ == '__main__':
    app.run()
    
        
