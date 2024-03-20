import streamlit as st
import openai
import os
import json
import requests
import math
import rag as kb
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tiktoken

  
openai.api_base = "https://gpt4enveastus2.openai.azure.com/"
openai.api_version = "2023-09-01-preview" ## "2023-08-01-preview"
openai.api_type = "azure"
openai.api_key = "" #"4e0ebbead66047609cb60ca2d0bc57f4"

flex_key = "pk_unity_2ae70138-d53b-11ed-be9b-7e87f65ba1ef"
lane_key = "pk_unity_2338e47e-4237-11ee-82d8-7e3f403a187c"
index_key = "pk_unity_2338e47e-4237-11ee-82d8-7e3f403a187c" # bmw data prep


def modify_attributes_and_values(data, attribute_to_change, new_value, target_dict, path=[]):
    if isinstance(data, dict):
        modified_data = {}
        for key, value in data.items():
            if key == attribute_to_change and path == target_dict:
                modified_data[key] = new_value
            else:
                modified_data[key] = modify_attributes_and_values(value, attribute_to_change, new_value, target_dict, path + [key])
        return modified_data
    elif isinstance(data, list):
        modified_data = []
        for item in data:
            modified_data.append(modify_attributes_and_values(item, attribute_to_change, new_value, target_dict, path))
        return modified_data
    else:
        return data


def delete_attributes(json_obj, attributes_to_delete):
    if isinstance(json_obj, dict):
        for key in list(json_obj.keys()):  # Convert to list to avoid modifying dict while iterating
            if key in attributes_to_delete:
                del json_obj[key]
            else:
                delete_attributes(json_obj[key], attributes_to_delete)
    elif isinstance(json_obj, list):
        for item in json_obj:
            delete_attributes(item, attributes_to_delete)

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


functions = [
    {
        "name": "get_rental_amount",
        "title": "Calculate Rental Amount Annuity",
        "description": "Get the rental amounts for a finance or lease loan. This funciton uses annuity method for calculation. The API used for this is available at https://docs.netsolapp.io/flex/index.html#tag/Rental-Calculation/paths/~1calculate~1RentalAmountAnnuity/post. This API is from Appex-Now Flex Calculation Engine",
        "parameters": {
            "type": "object",
            "properties": {
                "financedAmount": {
                    "type": "integer",
                    "description": "Total finance amount, assumed vales can be 32000, 51000, 10000, 540032 or 4002",
                },
                "apr": {
                    "type": "integer",
                    "description": "Interest Rate is a percentage value and is sometimes represented by a percentage sign. Default is 1.5",
                },
                "contractTerms": {
                    "type": "integer",
                    "description": "Total number of months or tenure, assumed value can be 12, 18, 24, 36, 48 or 64 months",
                },
                "rentalMode": {
                    "type": "string",
                    "description": "Payment Mode. Values can be 'Advance' or 'Arrear'",
                },
                "rentalFrequency": {
                    "type": "string",
                    "description": "Payment Frequency, values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'",
                },                  
            },
            "required": ["financedAmount","apr","contractTerms","rentalMode","rentalFrequency"],
        }
    },
    {
        "name": "get_rental_amount_flatplus",
        "title": "Calculate Rental Amount FlatPlus",
        "description": "Get the rental amounts for a finance or lease loan. This funciton uses Flat Plus method for calculation. The API used for this is available at https://docs.netsolapp.io/flex/index.html#tag/Rental-Calculation/paths/~1Calculate~1RentalAmountFlatPlus/post. This API is from Appex-Now Flex Calculation Engine",
        "parameters": {
            "type": "object",
            "properties": {
                "financedAmount": {
                    "type": "integer",
                    "description": "Total finance amount, assumed vales can be 32000, 51000, 10000, 540032 or 4002",
                },
                "apr": {
                    "type": "integer",
                    "description": "Interest Rate is a percentage value and is sometimes represented by a percentage sign. Default is 1.5",
                },
                "contractTerms": {
                    "type": "integer",
                    "description": "Total number of months or tenure, assumed value can be 12, 18, 24, 36, 48 or 64 months",
                },
                "rentalMode": {
                    "type": "string",
                    "description": "Payment Mode. Values can be 'Advance' or 'Arrear'",
                },
                "rentalFrequency": {
                    "type": "string",
                    "description": "Payment Frequency, values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'",
                },                  
            },
            "required": ["financedAmount","apr","contractTerms","rentalMode","rentalFrequency"],
        }
    },    
    {
        "name": "get_finance_amount_affordability",
        "description": "Calculates finance amount in order to check affordability of a finance or lease loan based on parameters such as rentals, downpayment, rental frequency, rental mode, contract terms and interest rate. This method is very useful in calculating if a finance or lease loan is affordable or not interms of financed amount. The API used for this is available at https://docs.netsolapp.io/flex/index.html#tag/Affordability/paths/~1calculate~1ReverseFinanceAmount/post. This API is from Appex-Now Flex Calculation Engine",
        "parameters": {
            "type": "object",
            "properties": {
                "RentalAmount": {
                    "type": "integer",
                    "description": "Rental Amount or Payment for the loan, assumed vales can be 400, 1000, 1400 or 2000. This is the payment made periodically for the repayment of a loan or lease. This can be monthly, Semi-Annually, Quarterly, Annually, Weekly or Fortnightly.",
                },
                "DownPayment": {
                    "type": "integer",
                    "description": "Total Down Payment / Upfront Payment / Deposit. It is required value that has to be greater then or equal to 1. If not provided assume it to be 1",
                },
                "interestRate": {
                    "type": "integer",
                    "description": "Interest Rate is a percentage value and is sometimes represented by a percentage sign. Default is 1.5",
                },
                "contractTerms": {
                    "type": "integer",
                    "description": "Total number of months or tenure, assumed value can be 12, 18, 24, 36, 48 or 64 months",
                },
                "rentalMode": {
                    "type": "string",
                    "description": "Payment Mode. Values can be 'Advance' or 'Arrear'. Default is 'Arrear'",
                },
                "rentalFrequency": {
                    "type": "string",
                    "description": "Payment Frequency, values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'. Default is Monthly",
                },                  
            },
            "required": ["RentalAmount","DownPayment","interestRate","contractTerms","rentalMode","rentalFrequency"],
        }
    },
    {
        "name": "get_downpayment_amount_affordability",
        "description": "Calculates down payment amount in order to check affordability of a finance or lease loan based on parameters such as rentals, finace amount, rental frequency, rental mode, contract terms and interest rate. This method is very useful in calculating if a finance or lease loan is affordable or not interms of downpayment. The API used for this is available at https://docs.netsolapp.io/flex/index.html#tag/Affordability/paths/~1calculate~1ReverseDownPayment/post. This API is from Appex-Now Flex Calculation Engine",
        "parameters": {
            "type": "object",
            "properties": {
                "RentalAmount": {
                    "type": "integer",
                    "description": "Rental Amount or Payment for the loan, assumed vales can be 400, 1000, 1400 or 2000. This is the payment made periodically for the repayment of a loan or lease. This can be monthly, Semi-Annually, Quarterly, Annually, Weekly or Fortnightly.",
                },
                "financedAmount": {
                    "type": "integer",
                    "description": "Total finance amount, assumed vales can be 32000, 51000, 10000, 540032 or 4002",
                },
                "interestRate": {
                    "type": "integer",
                    "description": "Interest Rate, assumed values can be 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0 or 4.5. Default is 1.5 ",
                },
                "contractTerms": {
                    "type": "integer",
                    "description": "Total number of months or tenure, assumed value can be 12, 18, 24, 36, 48 or 64 months",
                },
                "rentalMode": {
                    "type": "string",
                    "description": "Payment Mode. Values can be 'Advance' or 'Arrear'. Default is 'Arrear'",
                },
                "rentalFrequency": {
                    "type": "string",
                    "description": "Payment Frequency, values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'. Default is Monthly",
                },                  
            },
            "required": ["RentalAmount","financedAmount","interestRate","contractTerms","rentalMode","rentalFrequency"],
        }
    }
    ,{
        "name": "get_reverse_calculation_duration",
        "description": "This function calculates the total number of payment, total number of terms by taking finance amount, annual rate, rental amount, rate conversion method, rental frequency, rental mode and maximum number of payments as parameters and returns total payments and total terms. The API used for this is available at https://docs.netsolapp.io/flex/index.html#tag/Affordability/paths/~1calculate~1ReverseCalculateDuration/post. This API is from Appex-Now Flex Calculation Engine",
        "parameters": {
            "type": "object",
            "properties": {
                "financeAmount": {
                    "type": "integer",
                    "description": "Total finance amount, assumed vales can be 32000, 51000, 10000, 540032 or 4002",
                },
                "annualRate": {
                    "type": "integer",
                    "description": "Annual rate or Interest Rate, assumed values can be 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0 or 4.5. Default is 1.5 ",
                },
                "rentalAmount": {
                    "type": "integer",
                    "description": "Rental Amount or Payment for the loan, assumed vales can be 400, 1000, 1400 or 2000. This is the payment made periodically for the repayment of a loan or lease. This can be monthly, Semi-Annually, Quarterly, Annually, Weekly or Fortnightly.",
                },
                "rentalFrequency": {
                    "type": "string",
                    "description": "Payment Frequency, values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'. Default is Monthly",
                },     
                "rentalMode": {
                    "type": "string",
                    "description": "Payment Mode. Values can be 'Advance' or 'Arrear'. Default is 'Arrear'",
                }                           
            },
            "required": ["financeAmount","annualRate","rentalAmount","rentalFrequency","rentalMode"],
        }    
    }
    ,{
        "name": "get_programs",
        "description": "This function returns all available programs or deals based on the given parameters such as asset make, asset model, asset model details or trim. Dealer ID can be obtained from get_all_dealers function and asset make, asset model, asset model details or trim can be obtained from get_asset_configurations function. The API used for this is available at https://docs.netsolapp.io/index/index.html#tag/Programs-Evaluation/operation/get_all_evaluated_programs_config_programs_all__post.  This API is from Appex-Now Flex Calculation Engine.",
        "parameters": {
            "type": "object",
            "properties": {
                # "terms": {
                #     "type": "integer",
                #     "description": "Total number of months or tenure, assumed value can be 12, 18, 24, 36, 48 or 64 months",
                # },
                "dealer_id": {
                    "type": "integer",
                    "description": "A unique integer id used to identify the dealer. Dealer id is available from get_all_dealers function which returns multiple records. Ask the user to select which dealer to use and use its dealer id",
                },
                "asset_make_id": {
                    "type": "integer",
                    "description": "A unique integer id used to identify the asset make. Asset make description and ID are available from get_asset_configurations function.",
                },
                "asset_model_id": {
                    "type": "integer",
                    "description": "A unique integer id used to identify the asset model. Asset model description and ID are available from get_asset_configurations function.",
                },
                "asset_model_detail_id": {
                    "type": "integer",
                    "description": "A unique integer id used to identify the asset model details or trim. Asset model deteails description and ID are available from get_asset_configurations function as Trim",
                },
                "make_name": {
                    "type": "string",
                    "description": "Asset make name. Asset Make details are available from get_asset_configurations function.",
                },
                # "model_name": {
                #     "type": "string",
                #     "description": "Asset model name.",
                # },
                "model_detail_name": {
                    "type": "string",
                    "description": "Asset model detailed name or trim",
                },
            #     "asset_condition": {
            #         "type": "string",
            #         "description": "Asset condition, new, used or old.",
            #     },                                                                                                
            #     "credit_rating": {
            #         "type": "string",
            #         "description": "Credit ratings",
            #     },
            #     "finance_type": {
            #         "type": "string",
            #         "description": "Finance type",
            #     },
            #     "asset_classification": {
            #         "type": "string",
            #         "description": "Asset classifications such as vehicle or equipment",
            #     },                                
            #     "annual_usage": {
            #         "type": "integer",
            #         "description": "Annual usage of the asset.",
            #     },
            #    "rental_mode": {
            #         "type": "string",
            #         "description": "Payment Mode. Values can be 'Advance' or 'Arrear'. Rental or payment mode available with the program",
            #     },
            #    "rental_frequency": {
            #         "type": "string",
            #         "description": "Payment frequency available with the program. values can be 'Monthly', 'SemiAnnual', 'Quarterly', 'Annual', 'Weekly','Fortnightly'. Default is Monthly  ",
            #     },
            #     "finance_amount": {
            #         "type": "integer",
            #         "description": "Total finance amount.",
            #     }                        
            },
            "required": ["dealer_id","asset_make_id","asset_model_id","asset_model_detail_id","make_name"],
        }
    }
    ,{
        "name": "get_lender",
        "description": "This function gets the Lender details from the system. Lender details include lender id, name and other details. Lender id is used for calling other other functions. The API used for this is available at https://docs.netsolapp.io/index/index.html.  This API is from Appex-Now Index." ,
        "parameters": {
            "type": "object",
            "properties": {},

        }
    }
    ,{
        "name": "get_inventory",
        "description": "This function gets all vehicles details records from inventory management The API used for this is available at https://docs.netsolapp.io/index/index.html#tag/Inventory-Management/operation/get_inventory_by_parameter_config_inventory_filter_get. This API is from Appex-Now Index.",
        "parameters": {
            "type": "object",
            "properties": {
                "dealer_code": {
                    "type": "string",
                    "description": "Dealer code is a unique string value given to the dealer. It used to identify the dealer in addition to its ID. Dealer code against dealers configured in the system can be obtainted by get_all_dealers function. Do not assume its value if it is not available from the get_all_dealers function ask the user to provide it.",
                },
                "internet_price_from": {
                    "type": "integer",
                    "description": "This is a range filter for internet price 'from' value. Its default value is 0 and can vary based on user input.",
                },
                "internet_price_to": {
                    "type": "integer",
                    "description": "This is a range filter for internet price 'to' value.",
                }                                        
            },
            "required": ["dealer_code"],
        }    
    }
    ,{
        "name": "get_all_dealers",
        "description": "This function gets all active dealers in the system. Function can be used to get details of a dealer as lender id is required parameter and if not available can be obtained from function get_lender. The API used for this is available at https://docs.netsolapp.io/index/index.html. This API is from Appex-Now Index.",
        "parameters": {
            "type": "object",
            "properties": {
                "lender_id": {
                    "type": "integer",
                    "description": "An id that uniquely identifies a lender. If not available, it can be obtained by get_lender function, which returns all the details against the lender configured in the system including lender id.",
                }                       
            },
            "required": ["lender_id"],
        }    
    }
    ,{
        "name": "get_asset_configurations",
        "description": "This function returns all asset configurations in the system. It can be used to list Asset Make, Asset Models and Asset Models Trims. Configurations include Asset Make, Asset Model, and Asset Model Detail or Trim. This information is used in get_programs function. The API used for this is available at https://docs.netsolapp.io/index/index.html. This API is from Appex-Now Index.",
        "parameters": {
            "type": "object",
            "properties": {
                "lender_id": {
                    "type": "integer",
                    "description": "An id that uniquely identifies a lender. If not available, it can be obtained by get_lender function, which returns all the details against the lender configured in the system including lender id.",
                }                       
            },
            "required": ["lender_id"],
        }    
    }
    ,{
        "name": "get_finance_insurance_products",
        "description": "This functions return finance and insurance products also known as f&i products from the sytem. The API used for this is available at https://docs.netsolapp.io/index/index.html. This API is from Appex-Now Index." ,
        "parameters": {
            "type": "object",
            "properties": {},

        }
    }
    ,{
        "name": "get_workqueue",
        "description": "This functions returns all Orders from the system workqueue. The API used for this is available at https://docs.netsolapp.io/lane/lane.html. This API is from Appex-Now Lane." ,
        "parameters": {
            "type": "object",
            "properties": {
                "order_status": {
                    "type": "string",
                    "description": "It is a filter parameter for the Order status. If provided only orders with those statuses will be retrieved from workqueue. If not provided all orders will be retrived from workqueue. Possible value are 'Draft', 'Cancelled', 'Appointment Scheduled', 'Awaiting Scheduling', 'Completed' and 'Conditioned'",
                }                       
            },
            "required": ["order_status"],
        }
    }
    ,{
        "name": "send_email",
        "description": "This functions is used to send emails." ,
        "parameters": {
            "type": "object",
            "properties": {
                "body": {
                    "type": "string",
                    "description": "This is the body of the email.",
                },
                "to_email": {
                    "type": "string",
                    "description": "This parameter is the email id of the person who we want to send email to.",
                },
                "CC": {
                    "type": "string",
                    "description": "This parameter is the email id of the person who we want to send copy of the email",
                }                                                       
            },
            "required": ["to_email","body"],
        }
    }
    ,{
        "name": "get_customer",
        "description": "This function retrieves customers based on reference_id of the customer. This function returns customer email address, name and other details. It can be used to retrieve emails of customer by reference_id." ,
        "parameters": {
            "type": "object",
            "properties": {
                "reference_id": {
                    "type": "string",
                    "description": "A unique string identifier for the customer.",
                }                                     
            },
            "required": ["reference_id"],
        }
    }       
]


def call_post_endpoint_with_api_key(url, data, key, method='POST', custom_header=""):
    headers = {
        'x-api-key': key,
        'Content-Type': 'application/json'  
    }

    if custom_header != "":
        headers = custom_header

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

            # If the API returns JSON data in the response, you can access it like this:
            response_data = response.json()
            return response_data

        if method == "POST":
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

            # If the API returns JSON data in the response, you can access it like this:
            response_data = response.json()
            return response_data

    except requests.exceptions.RequestException as e:
        # Handle any request-related errors (e.g., connection error, timeout, etc.)
        print("Error in API:", e)
        return None


def get_finance_amount_affordability(request):

    payload = { "interestRate": request.get("interestRate"), "rentalMode": ""+request.get('rentalMode')+"", "rentalFrequency": ""+request.get("rentalFrequency")+"", "rvAmount": 0, "contractTerms": request.get('contractTerms'), "structureRental": [{ "startTerm": 1, "endTerm": request.get('contractTerms'), "rentalType": "Auto", "amount": request.get("RentalAmount") }], "DownPayment" : request.get("DownPayment")  }

    response_data = call_post_endpoint_with_api_key('https://dev-api.netsolapp.io/marketplace/calculate/ReverseFinanceAmount', payload, flex_key)
    
    print("ReverseFinanceAmount Payload: "+json.dumps(payload))
    return response_data

def get_rental_amount(request):
    payload = { "requestParam": { "apr": request.get("apr"), "contractTerms": request.get('contractTerms'), "rentalMode": ""+request.get('rentalMode')+"", "rentalFrequency": ""+request.get("rentalFrequency")+"", "financedAmount": request.get("financedAmount")}}

    response_data = call_post_endpoint_with_api_key('https://dev-api.netsolapp.io/marketplace/calculate/RentalAmountAnnuity', payload, flex_key)
    
    print("RentalAmountAnnuity Payload: "+json.dumps(payload))
    return response_data

def get_rental_amount_flatplus(request):
    payload = { "requestParam": { "apr": request.get("apr"), "contractTerms": request.get('contractTerms'), "rentalMode": ""+request.get('rentalMode')+"", "rentalFrequency": ""+request.get("rentalFrequency")+"", "financedAmount": request.get("financedAmount")}}

    response_data = call_post_endpoint_with_api_key('https://dev-api.netsolapp.io/marketplace/calculate/RentalAmountFlatPlus', payload, flex_key)
    
    print("get_rental_amount_flatplus Payload: "+json.dumps(payload))
    return response_data

def get_downpayment_amount_affordability(request):
    payload = { "interestRate": request.get("interestRate"), "rentalMode": ""+request.get('rentalMode')+"", "rentalFrequency": ""+request.get("rentalFrequency")+"", "rvAmount": 0, "contractTerms": request.get('contractTerms'), "structureRental": [{ "startTerm": 1, "endTerm": request.get('contractTerms'), "rentalType": "Auto", "amount": request.get("RentalAmount") }], "financedAmount" : request.get("financedAmount")  }

    response_data = call_post_endpoint_with_api_key('https://dev-api.netsolapp.io/marketplace/calculate/ReverseDownPayment', payload, flex_key)
    
    print("ReverseDownPayment Payload: "+json.dumps(payload))
    return response_data


def get_reverse_calculation_duration(request):
    payload = { "financeAmount": request.get("financeAmount"), "annualRate": request.get("annualRate"),"rentalAmount": request.get("rentalAmount"), "rentalFrequency": ""+request.get("rentalFrequency")+"", "rentalMode": ""+request.get("rentalMode")+""}

    response_data = call_post_endpoint_with_api_key('https://dev-api.netsolapp.io/marketplace/calculate/ReverseCalculateDuration', payload, flex_key)
    
    print("ReverseCalculateDuration Payload: "+json.dumps(payload))
    return response_data

def get_programs(request):
    try:
        print("get_programs Request Payload: "+json.dumps(request))

        # payload = { "terms": request.get("terms"), 
        #         "dealer_id": request.get("dealer_id"),
        #         "asset_make_id": request.get("asset_make_id"), 
        #         "asset_model_id": request.get("asset_model_id"), 
        #         "asset_model_detail_id": request.get("asset_model_detail_id"), 
        #         "make_name": ""+request.get("make_name")+"", 
        #         "model_name": ""+request.get("model_name")+"",
        #         "model_detail_name": ""+request.get("model_detail_name")+"",
        #         "asset_condition": ""+request.get("asset_condition")+"",
        #         "credit_rating": ""+request.get("credit_rating")+"",
        #         "finance_type": ""+request.get("finance_type")+"",
        #         "asset_classification": ""+request.get("asset_classification")+"",
        #         "annual_usage": request.get("annual_usage"),
        #         "rental_mode":""+ request.get("rental_mode")+"",
        #         "rental_frequency":""+ request.get("rental_frequency")+"",
        #         "finance_amount":request.get("finance_amount")
        #         }
    
    except Exception as e:
        st.error("An internal error occured. Please check logs for details.")
        print("Exception: ",e)
        return ""

    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/programs/all/', request, index_key)
    
    #print("get_programs Payload: "+json.dumps(payload))
    return response_data

def get_lender(request):
    payload = ""

    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/lender_by_api_key', payload, index_key, 'GET')
    
    print("get_lender Payload: "+json.dumps(payload))
    return response_data


def get_inventory(request):
    print("get_inventory request payload form GPT: "+json.dumps(request))
    payload = { "dealer_code": ""+request.get("dealer_code")+"", "page_number": 0, "page_size": 10, "vehicle_status": "Available", "internet_price_from": request.get("internet_price_from"), "internet_price_to": request.get("internet_price_to")}

    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/inventory/filter', payload, index_key, 'GET')
    #data = json.loads(response_data)

    attributes_to_remove = ["created_at", "listing_status","updated_at", "daily_update", "key_id","dealer_options","dealer_url","comments_from_mini","stock_number","engine_configuration","interior_color_manufacturer_code","non_package_option_codes","is_updated","is_deleted","transmission_speed","engine_displacement","non_package_option_descriptions","container_file_name","phone_number","engine_induction","option_description","fax","stock_photos","dealer_location_id","package_code_option_code_id","packages_and_option_description_id","packages_and_option_description","package_code_option_code"]

    delete_attributes(response_data, attributes_to_remove)

    print("get_inventory response modified: "+json.dumps(response_data))
    
    return response_data

def get_all_dealers(request):
    payload = ""
    lender = str(request.get("lender_id"))
    headers = {
        'x-api-key': index_key,
        'Content-Type': 'application/json',
        'lender_id': lender
    }
    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/dealers/active', payload, index_key, 'GET', headers)
    
    print("get_all_dealers Payload: "+json.dumps(payload))
    return response_data

def get_asset_configurations(request):
    payload = ""
    lender = str(request.get("lender_id"))
    headers = {
        'x-api-key': index_key,
        'Content-Type': 'application/json',
        'lender_id': lender
    }
    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/asset-make', payload, index_key, 'GET', headers)
    
    print("get_asset_configurations before: "+json.dumps(response_data))
    
    modify_attributes_and_values(response_data, "id", "asset_make_id",[])
    modify_attributes_and_values(response_data, "id", "asset_model_id","asset_models")
    modify_attributes_and_values(response_data, "id", "asset_model_detail_id","asset_trims")
    
    print("get_asset_configurations after: "+json.dumps(response_data))

    return response_data

def get_finance_insurance_products(request):
    payload = ""

    response_data = call_post_endpoint_with_api_key('https://config-api-demo.netsolapp.io/config/financial-insurance', payload, index_key, 'GET')
    
    print("get_finance_insurance_products Payload: "+json.dumps(payload))
    return response_data

def get_workqueue(request):
    payload = {"page_number": 0, "page_size": 50, "multiple_order_status":""+request.get("order_status")+""}

    response_data = call_post_endpoint_with_api_key('https://dms-api-demo.netsolapp.io/dms/configure/workqueue/search', payload, lane_key, 'GET')
    
    print("get_workqueue Payload: "+json.dumps(payload))
    return response_data



def send_email(request):
    print("send_email Payload: "+json.dumps(request))
    subject = "Communication from Farabi"
    body=""+request.get("body")+""
    to_email=""+request.get("to_email")+""
    gmail_user='alam.mohsin@gmail.com'
    gmail_password="qixkvdmjzcxfbkeq"
    CC=request.get("CC")

    # Create a MIMEText object to represent the email body
    msg = MIMEMultipart()
    msg.attach(MIMEText(body, 'plain'))

    # Set the email subject
    msg['Subject'] = subject

    # Set the sender's and recipient's email addresses
    msg['From'] = f'Farabi Agent <{gmail_user}>' 
    msg['To'] = to_email

    if CC:
        msg['CC'] = CC

    try:
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Start TLS encryption

        # Login to your Gmail account
        server.login(gmail_user, gmail_password)

        # Send the email
        server.sendmail(gmail_user, to_email, msg.as_string())

        # Close the connection
        server.quit()
        print("Email sent successfully!")
        response_data = "Email sent to "+to_email
        return response_data
    
    except Exception as e:
        print(f"Error: {e}")

def get_customer(request):
    payload = {"reference_id": ""+request.get("reference_id")+""}

    response_data = call_post_endpoint_with_api_key('https://dms-api-demo.netsolapp.io/dms/customer', payload, lane_key, 'GET')
    
    print("get_customer Payload: "+json.dumps(payload))
    return response_data

def func_response(query):
    sys_message = {"role": "system", "content": """Assume you are a helpful BMW car dealer assistant that helps users get answers to questions using provided functions and conversation history. While calling functions if a value is not available use default values provided in this prompt, if default values are not available make assumptions for values that need you need to plug into the functions. If the request is ambiguous, use conversation history to respond otherwise Ask for clarification. 
        
        Respond in markdown. 
         
        Do not display currency symbols with amounts.  

        Use given default values for parameters in different functions.
        lender_id=2847
        dealer_code='00001'
        dealer_id=2703
        make_name='BMW'  

        If user asks to send email, make sure the body of the email is written in professional tone.

        If user asks for existing programs, use get_asset_configurations function to get asset_make_id, asset_model_id and asset_model_detail_id based on the information from get_inventory function.
         
        Please ask the customer if they are interested in knowing more about product offerings, mentioning the products based on the conversation history, in the form of succinct questions. When user responds with affirmative for example Yes or Ok; consider it a response to succinct question you asked in your response.
          """}

    # st.session_state.messages.append(sys_message)

# At the end of the response list down is grey color the API links from the description of functions called for the response, in case of multiple calls to the function list its API link only once.

    while True:
        # print(messages)
        # print("Total Tokens Phase-1: " + str(num_tokens_from_messages(messages,model="gpt-4-32k-0613")))

        messages_for_gpt=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        messages_for_gpt.append(sys_message)

        response_function_selection = openai.ChatCompletion.create(
            deployment_id="gpt432k",
            messages=messages_for_gpt,
            functions=functions,
            temperature=0.5,
        )
        
        print("START: ----------------response_function_Parameter_selection-----------------")
        print(response_function_selection)
        print("End: ----------------response_function_Parameter_selection-----------------")

        if response_function_selection["choices"][0]["finish_reason"] == 'stop' :
            return response_function_selection.choices[0].message.content.strip()

        function_call =  response_function_selection.choices[0].message.function_call

        st.session_state.messages.append(
            {
                "role": response_function_selection.choices[0].message["role"],
                "name": response_function_selection.choices[0].message["function_call"]["name"],
                "content": response_function_selection.choices[0].message["function_call"]["arguments"],
            }
        )
            
        if function_call.name == "get_rental_amount":
            response = get_rental_amount(json.loads(function_call.arguments))
            
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_rental_amount",
                    "content": json.dumps(response)
                }
            )      

        if function_call.name == "get_rental_amount_flatplus":
            response = get_rental_amount_flatplus(json.loads(function_call.arguments))
            
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_rental_amount_flatplus",
                    "content": json.dumps(response)
                }
            )                

        if function_call.name == "get_finance_amount_affordability":
            response = get_finance_amount_affordability(json.loads(function_call.arguments))
            
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_finance_amount_affordability",
                    "content": json.dumps(response)
                }
            ) 

        if function_call.name == "get_downpayment_amount_affordability":
            response = get_downpayment_amount_affordability(json.loads(function_call.arguments))
            
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_downpayment_amount_affordability",
                    "content": json.dumps(response)
                }
            )        

        if function_call.name == "get_reverse_calculation_duration":
            response = get_reverse_calculation_duration(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_reverse_calculation_duration",
                    "content": json.dumps(response)
                }
            )  

        if function_call.name == "get_programs":
            response = get_programs(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_programs",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_lender":
            response = get_lender(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_lender",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_inventory":
            response = get_inventory(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_inventory",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_all_dealers":
            response = get_all_dealers(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_all_dealers",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_asset_configurations":
            response = get_asset_configurations(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_asset_configurations",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_finance_insurance_products":
            response = get_finance_insurance_products(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_finance_insurance_products",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "get_workqueue":
            response = get_workqueue(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_workqueue",
                    "content": json.dumps(response)
                }
            )

        if function_call.name == "send_email":
            response = send_email(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "send_email",
                    "content": response
                }
            )

        if function_call.name == "get_customer":
            response = get_customer(json.loads(function_call.arguments))
        
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": "get_customer",
                    "content": json.dumps(response)
                }
            )            

        #print("Total Tokens Phase-2: " + str(num_tokens_from_messages(messages,model="gpt-4-32k-0613")))
        # make sense of the response from the api call

        messages_for_gpt_2=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        messages_for_gpt_2.append(sys_message)

        response = openai.ChatCompletion.create(
            deployment_id="gpt432k",
            messages=messages_for_gpt_2,
            functions=functions,
            temperature=0.5,
        )


        print("START: ----------------function_completion-----------------")
        print(response)
        print("End: ----------------function_completion-----------------")

        if response["choices"][0]["finish_reason"] != 'function_call' or response["choices"][0]["finish_reason"] == 'stop' :
            return response.choices[0].message.content.strip()    