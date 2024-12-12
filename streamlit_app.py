import streamlit as st
from openai import AzureOpenAI
from PIL import Image
client = AzureOpenAI(
  azure_endpoint = "https://gpt4enveastus2.openai.azure.com/", 
  api_key="64eaa32ab00a4e50bdd0c11f398515d2",  
  api_version="2024-02-01", #"2023-05-15"#"2024-02-15-preview"
)
# openai.api_base = "https://gpt4enveastus2.openai.azure.com/"
# openai.api_version = "2023-05-15" # "2023-09-01-preview" ## "2023-08-01-preview"
# openai.api_type = "azure"
# openai.api_key =  "4e0ebbead66047609cb60ca2d0bc57f4"
deployment_id = "chatbot1106"#"chatbot1106"#"gpt432k"
# openai.api_key = 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
image_logo = Image.open('pngegg.png')
st.set_page_config(page_title="Chatbot", layout="centered", initial_sidebar_state="collapsed", menu_items=None,)
instructions = "Please ask the user about a) location, b) plans to own the vehicle long term or short term, and c) use of vehicle for commuting or weekend driving, and d) are you leasing or financing, so that you can suggest appropriate finance and insurance products. Start the conversation by introducing yourself first."
questions_instructions = ""
with st.sidebar:
    st.session_state.params = st.experimental_get_query_params()
    # st.write(st.session_state.params)
    temp = ""
    if st.session_state.params != "":
        if "location" in st.session_state.params.keys():
            #st.write("Location: " +st.session_state.params["location"][0])
            location_instruction = "User is located in " + st.session_state.params["location"][0]+". "
            temp = temp + location_instruction
        else:
            questions_instructions = questions_instructions + "Please ask the user about location. "
        if "duration" in st.session_state.params.keys():
            #st.write("duration: " +st.session_state.params["duration"][0])
            duration_instruction = "User wants to own  vehicle for " + st.session_state.params["duration"][0]+". "
            temp = temp + duration_instruction
        else:
            questions_instructions = questions_instructions + "Please ask the user about plans to own the vehicle long term or short term. "
        if "usage" in st.session_state.params.keys():
            #st.write("usage: " +st.session_state.params["usage"][0])
            usage_instruction = "User want to use vehicle for " + st.session_state.params["usage"][0]+" purpose. "
            temp = temp + usage_instruction
        else:
            questions_instructions = questions_instructions + "Please ask the user about use of vehicle for commuting or weekend driving. "
        if "deal_type" in st.session_state.params.keys():
            #st.write("deal_type: " +st.session_state.params["deal_type"][0])
            deal_type_instruction = "User wants to " + st.session_state.params["deal_type"][0]+" the vehicle. "
            temp = temp + deal_type_instruction
        else:
            questions_instructions = questions_instructions + "Please ask the user about leasing or financing the vehicle. "            
        if "name" in st.session_state.params.keys():
            #st.write("name: " +st.session_state.params["name"][0])
            name_instruction = "User name is " + st.session_state.params["name"][0]+", use this name to communicate with user. "
            temp = temp + name_instruction
        
        if "vehicle" in st.session_state.params.keys():
            #st.write("Vehicle: " +st.session_state.params["vehicle"][0])
            vehicle_instruction = "User has selected  model " + st.session_state.params["vehicle"][0]+" for the deal. "
            temp = temp + name_instruction
            if "vehicle_image" in st.session_state.params.keys():
                #st.write("vehicle_image: " +st.session_state.params["vehicle_image"][0])
                vehicle_image_instruction = " model image is: " + st.session_state.params["vehicle_image"][0]+". "
                temp = temp + vehicle_image_instruction
        instructions = f"Use the following information provided by user, so that you can suggest appropriate finance and insurance products. {temp} Start the conversation by introducing yourself first."
system_role = """
        Assume that you are a vehicle dealer assistant that responds in markdown format. A customer is interested in buying a vehicle and may have selected a vehicle, check conversation history to verify. Your goal is to negotiate and upsell long term finance and insurance product offerings for the Vehicle. In case the customer declines a service, creatively ask for the reason and capture the answers for the manager for review.
    
        The following product offerings are available with their costs terms and average repair cost:
            - Extended Warranty / Vehicle Service Contract : cost is $1999.00 for 36 months and average repair cost is $3200.00.
            - Pre-paid Maintenance Contract : cost is $1999.00 for 36 months and average repair cost is $4500.00.
            - GAP Insurance (Standard): cost is $1199.00 for 36 month and average cost for claim is $3000.00.
            - Tire & Wheel Protection (with Cosmetric coverage) : cost is $1936.00 for 36 months and average repair cost is $3000.00.
            - Tire & Wheel Protection : cost is $14666.00 for 36 months and average repair cost is $2500.00.
            - Dent Protection : cost is $4100.00 for 36 months and average repair cost is $200.00.
            - Key Replacement : cost is $2700.00 for 36 months and average replacement cost is $100.00.
            - Windshield Protection : cost is $2620.00 for 36 months and average replacement cost is $350.00.
            - Stolen Vehicle Tracking and Recovery System : cost is $1000.00 for 36 months and average replacement is cost of vehicle itself
        Your goal is sell the appropriate product offerings to the customer. The chances of the customer buying a product depends on: 
            1. How long customer intends to be the vehicle owner. If customer is planning to be a long term owner then customer would be interested in extended warranty.
	@@ -99,21 +99,21 @@
            5. Offer GAP Insurance and Key Replacement insurance to the customer if they want to finance the vehicle.
        Crime and Road Statistics by city are as follows:
            - Chicago, Crime=Low, Roads=Good, 11.21% crime below compared to national average
            - New York, Crime=Low, Roads=Good, 19.07% crime below compared to national average
            - Los Angeles, Crime=Low, Roads=Bad, 40.33% crime below compared to national average
            - Kentucky, Crime=High, Roads=Good, 27.38% crime above compared to national average
            - California, Crime=Low, Roads=Good, 51.57% crime below compared to national average
            - Miami, Crime=High, Roads=Bad, 48.91% crime above compared to national average
            - Phoenix, Crime=Medium, Roads=Good, 4.50% crime below compared to national average
            - St Louis, Crime=High, Roads=Bad, 33.98% crime above compared to national average
            - San Diego, Crime=Low, Roads=Good, 45.71% crime below compared to national average
            - Bel Air, Crime=Low, Roads=Good, 11.21% crime above compared to national average
            - Calabasas, Crime=High, Roads=Good, 23.55% crime above compared to national average             
        Please ask customer terse questions to get this information if the information has been provided show in summarized form and if user asks for details then show the average cost to repair/replace with crime rate and road conditions. Using this information, please show the average monthly cost for these products, and also ask the customer if they are interested in knowing more about specific product offerings, mentioning the products based on customer's info, in the form of terse questions. If customer asks a question in response, reply from the information given in this prompt. Please feel free to ask questions to the customer to get the information needed to select the products.
    
        Always stay in character as a  vehicle dealer assistant.Respond in the same language as request. If question is asked in chinese response in chinese. Be terse in your answers but with all relevant information in summarized form. Always sell the Pre-paid Maintenance Contract with all sales. Limit to only 3 products provided to customer in summarized form, display costs at first. Default language is english.
        """

if "messages" not in st.session_state.keys(): # Initialize the chat messages history
    st.session_state.messages = [
        {"role": "system", "content": system_role},
        {"role": "system", "content": f"Ask terse questions. {instructions} {questions_instructions}"}
    ]
if prompt := st.chat_input("Your question"): # Prompt for user input and save to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
for message in st.session_state.messages: # Display the prior chat messages
    if message["role"] == "assistant":
        with st.chat_message(message["role"],avatar=image_logo):
            st.markdown(message["content"], unsafe_allow_html=True)
    if message["role"] == "user":
        with st.chat_message(message["role"],avatar="👨‍💼"):
            st.markdown(message["content"], unsafe_allow_html=True)
# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant", avatar=image_logo):
        with st.spinner(" Generating Response ..."):
            message_placeholder = st.empty()
            full_response = ""  
            
            for response in client.chat.completions.create(
                model=deployment_id,
                messages=[{"role": m["role"], "content": m["content"]} 
                          for m in st.session_state.messages],
                stream=True,
                temperature=0
            ):
              
                #print('Response ',response)
                #print('Response length',len(response.choices))
                if len(response.choices) != 0:  
                  full_response += str(response.choices[0].delta.content).replace("$","&dollar;").replace("None","")
                  message_placeholder.markdown(full_response + " | ")
            #print('Completed Response ',response)
            message_placeholder.markdown(full_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            #with st.sidebar:
            #    st.write(st.session_state.messages)
