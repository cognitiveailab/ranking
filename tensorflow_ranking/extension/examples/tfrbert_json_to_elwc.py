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
import copy
import tfrbert_client_json 
import argparse

#
#   Main
#

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab_file", type=str, required=True, help="/path/to/bert_model/vocab.txt")
    parser.add_argument("--sequence_length", type=int, required=True, help="typically 128, 256, 512")    
    parser.add_argument("--input_file", type=str, required=True, help="JSON input filename (e.g. train.json)")
    parser.add_argument("--output_file", type=str, required=True, help="ELWC TFrecord filename (e.g. train.elwc.tfrecord)")

    parser.add_argument("--do_lower_case", action="store_true", help="Set for uncased models, otherwise do not include")

    args = parser.parse_args()

    print(args)
    #exit(1)

    # Parameters (model)
    #do_lower_case = True
    #sequence_length = 128

    # Parameters (in/out)
    #filenameJsonIn = "/home/peter/github/peter-ranking/ranking/jsonInExample-eval.json"
    #filenameELWCOut = "eval.toy.elwc.tfrecord"

    # Create helpers
    bert_helper = tfrbert_client_json.create_tfrbert_util_with_vocab(args.sequence_length, args.vocab_file, args.do_lower_case)
    bert_helper_json = tfrbert_client_json.TFRBertUtilJSON(bert_helper)

    # User output
    print("Utility to convert between JSON and ELWC for TFR-Bert")
    print("")
    print("Model Parameters: ")
    print("Vocabulary filename: " + args.vocab_file)
    print("sequence_length: " + str(args.sequence_length))
    print("do_lower_case: " + str(args.do_lower_case))

    print("\n")
    print("Input file:  " + args.input_file)
    print("Output file: " + args.output_file)


    # Example of converting from JSON to ELWC
    bert_helper_json.convert_json_to_elwc_export(args.input_file, args.output_file)

    print("Success.")



if __name__ == "__main__":
    main()

