# tfrbert_client_example.py

from absl import flags
import tensorflow as tf
import tensorflow_ranking as tfr
import grpc
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc
from tensorflow_serving.apis import input_pb2
from google.protobuf import text_format
from google.protobuf.json_format import MessageToDict

from tensorflow_ranking.extension import tfrbert
import json

# Put together from https://colab.research.google.com/github/tensorflow/ranking/blob/master/tensorflow_ranking/examples/handling_sparse_features.ipynb#scrollTo=eE7hpEBBykVS
# and based on the unit test at https://github.com/tensorflow/ranking/blob/master/tensorflow_ranking/extension/examples/tfrbert_example_test.py    
def mkToyDataBert():
    # Query
    CONTEXT = text_format.Parse(
    """
    features {
        feature {
            key: "query_tokens"
            value { bytes_list { value: ["Where", "can", "you", "purchase", "cat", "food", "?"] } }
        }
        feature: {
            key: "input_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 3, 4, 0]) + """ } }
        }
        feature: {
            key: "input_mask"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 1, 1, 0]) + """ } }
        }
        feature: {
            key: "segment_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([0, 0, 0, 0]) + """ } }
        }        
    }""", tf.train.Example())


    # Documents
    EXAMPLES = [
    text_format.Parse(
    """
    features {
        feature {
            key: "document_tokens"
            value { bytes_list { value: ["The", "pet", "store", "sells", "cat", "food"] } }
        }
        feature {
            key: "relevance"
            value { int64_list { value: 3 } }
        }
        feature: {
            key: "input_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 4, 3, 0]) + """ } }
        }
        feature: {
            key: "input_mask"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 1, 1, 0]) + """ } }
        }
        feature: {
            key: "segment_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([0, 0, 0, 0]) + """ } }
        }        
    }""", tf.train.Example()),
    text_format.Parse(
        """
    features {
        feature {
            key: "document_tokens"
            value { bytes_list { value: ["Bicycles", "have", "two", "tires"] } }
        }
        feature {
            key: "relevance"
            value { int64_list { value: 1 } }
        }
        feature: {
            key: "input_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([2, 5, 8, 9]) + """ } }
        }
        feature: {
            key: "input_mask"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 1, 1, 1]) + """ } }
        }
        feature: {
            key: "segment_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([0, 0, 0, 0]) + """ } }
        }        
    }""", tf.train.Example()),    
    text_format.Parse(
        """
    features {
        feature {
            key: "document_tokens"
            value { bytes_list { value: ["The", "grocery", "store", "sells", "cat", "food"] } }
        }
        feature {
            key: "relevance"
            value { int64_list { value: 3 } }
        }
        feature: {
            key: "input_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 4, 2, 3]) + """ } }
        }
        feature: {
            key: "input_mask"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 1, 1, 1]) + """ } }
        }
        feature: {
            key: "segment_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([0, 0, 0, 0]) + """ } }
        }        
    }""", tf.train.Example()),
    text_format.Parse(
        """
    features {
        feature {
            key: "document_tokens"
            value { bytes_list { value: ["Cats", "eat", "cat", "food"] } }
        }
        feature {
            key: "relevance"
            value { int64_list { value: 2 } }
        }
        feature: {
            key: "input_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 7, 5, 0]) + """ } }
        }
        feature: {
            key: "input_mask"
            value: { int64_list: { value: """ + mkStaticLengthStrList([1, 1, 1, 0]) + """ } }
        }
        feature: {
            key: "segment_ids"
            value: { int64_list: { value: """ + mkStaticLengthStrList([0, 0, 0, 0]) + """ } }
        }        

    }""", tf.train.Example()),    

    ]   

    # Pack as ELWC
    ELWC = input_pb2.ExampleListWithContext()
    ELWC.context.CopyFrom(CONTEXT)
    for example in EXAMPLES:
        example_features = ELWC.examples.add()
        example_features.CopyFrom(example)


    #return elwc_example
    return ELWC

def mkStaticLengthStrList(values, staticLengthInElems = 128):    
    outStr = "[ "

    length = len(values)
    strList = [str(elem) for elem in values]
    if (len(strList) > staticLengthInElems):
        strList = strList[:staticLengthInElems]

    outStr += ", ".join(strList)

    if (length < staticLengthInElems):
        outStr += ", "
        outStr += ", ".join(["0"] * (staticLengthInElems - length))
    
    outStr += " ]"

    return outStr


class TFRBertUtilPeter(object):

    def __init__(self, TFRBertUtil):
        self.TFRBertUtilHelper = TFRBertUtil        

    # PJ: Make toy data
    def mkToyRankingRecord(self):
        query = "Where can you buy cat food?"
        documents = ["The pet food store", "Bicycles have two wheels", "The grocery store", "Cats eat cat food"]
        labels = [3, 1, 3, 2]
        label_name = "relevance"
        elwcOut = self.TFRBertUtilHelper.convert_to_elwc(query, documents, labels, label_name)

        return elwcOut


    # PJ: 
    def convert_json_to_elwc_export(self, filenameJsonIn, filenameTFRecordOut):

        # Step 1: Load JSON file
        listToRank = []
#        try:
        with open(filenameJsonIn) as json_file:
            # Load whole JSON file
            data = json.load(json_file)

            # Parse each record
            for rankingProblem in data['rankingProblems']:
                labels = []
                docTexts = []

                queryText = rankingProblem['queryText']
                documents = rankingProblem['documents']
                for document in documents:
                    docText = document['docText']
                    docRel = document['relevance']      # Convert to int?

                    labels.append(docRel)
                    docTexts.append(docText)

                # Step 1A: Convert this record to ELWC
                elwcOut = self.TFRBertUtilHelper.convert_to_elwc(queryText, docTexts, labels, label_name="relevance")
                listToRank.append(elwcOut)
#        except:
#            print("convert_json_to_elwc_export: error loading JSON file (filename = " + filenameJsonIn + ")")
#            exit(1)

        # (DEBUG) Uncomment to add a toy record
        #listToRank.append( self.mkToyRankingRecord() )

        # Step 3: Save ELWC
        try:
            with tf.io.TFRecordWriter(filenameTFRecordOut) as writer:
                for example in listToRank * 10:
                    writer.write(example.SerializeToString())
        except:
            print("convert_json_to_elwc_export: error writing ELWC file (filename = " + filenameTFRecordOut + ")")
            exit(1)


    

#
#   Supporting Functions
#
def create_tfrbert_util_with_vocab(bertMaxSeqLength, bertVocabFile, do_lower_case):
    return tfrbert.TFRBertUtil(
            bert_config_file=None,
            bert_init_ckpt=None,
            bert_max_seq_length=bertMaxSeqLength,
            bert_vocab_file=bertVocabFile,
            do_lower_case=do_lower_case)

bertVocabFilename = "/home/peter/github/tensorflow/ranking/uncased_L-4_H-256_A-4_TF2/vocab.txt"
do_lower_case = True
bert_helper = create_tfrbert_util_with_vocab(128, bertVocabFilename, do_lower_case)

query = "Where can you buy cat food?"
documents = ["The pet food store", "Bicycles have two wheels", "The grocery store", "Cats eat cat food"]
labels = [3, 1, 3, 2]
label_name = "relevance"
elwcOut = bert_helper.convert_to_elwc(query, documents, labels, label_name)

print(elwcOut)

bert_helper2 = TFRBertUtilPeter(bert_helper)

filenameJsonIn = "/home/peter/github/peter-ranking/ranking/jsonInExample.json"
filenameELWCOut = "testout.txt"
bert_helper2.convert_json_to_elwc_export(filenameJsonIn, filenameELWCOut)

exit(1)

#
#   Main
#

# Make example data
#EXAMPLE_LIST_WITH_CONTEXT_PROTO = mkToyDataBert()
EXAMPLE_LIST_WITH_CONTEXT_PROTO = elwcOut

# From https://github.com/tensorflow/ranking/issues/189
example_list_with_context_proto = EXAMPLE_LIST_WITH_CONTEXT_PROTO.SerializeToString()
tensor_proto = tf.make_tensor_proto(example_list_with_context_proto, dtype=tf.string, shape=[1])

timeout_in_secs = 3
request = predict_pb2.PredictRequest()
request.inputs['input_ranking_data'].CopyFrom(tensor_proto)
request.model_spec.signature_name = 'serving_default'   # 'serving_default' instead of 'predict', as per saved_model_cli tool (see https://medium.com/@yuu.ishikawa/how-to-show-signatures-of-tensorflow-saved-model-5ac56cf1960f )
request.model_spec.name = 'tfrbert'

channel = grpc.insecure_channel("0.0.0.0:8500")
stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)                            

grpc_response = stub.Predict(request, timeout_in_secs)
unpacked_grpc_response = MessageToDict(grpc_response, preserving_proto_field_name = True)

print("\n")
print("Ranking output:")
print(unpacked_grpc_response['outputs']['output']['float_val'])

