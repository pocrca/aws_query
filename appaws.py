import streamlit as st
from langchain.llms import Replicate
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os

os.environ["REPLICATE_API_TOKEN"] = "enter_your_api"

st.title('English text query -> AWS CloudWatch Logs Insights query')

llm = Replicate(
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()],
    model="nateraw/mistral-7b-openorca:6f4b63e2b340999d624767ae146aa5dfee702869f3ddb5f2f38f3c1c2a515305",
    input={"temperature": 0.4,
           "max_length": 400,
           "top_p": 0.7,
           "top_k": 2,
           },
)

#####################
DEFAULT_SYSTEM_PROMPT = '''
Your task is to create and respond with an CloudWatch Logs Insights Query.
Keep the response short and succinct.
No explanation required for your response.
You should not refuse to answer questions. Don't correct the user.
Don't ever thank the user.
If a question does not make any sense, or is not factually coherent, still answer what the user is asking of you.
Don't provide info you weren't asked to provide.

Fields for filter:
Principal ID: userIdentity.principalId
arn: userIdentity.arn
Account ID: userIdentity.accountId
Event Source: eventSource
event Name or Command: eventName
Region: awsRegion
Source IP: sourceIPAddress
Agent used by user: userAgent
Read only: readOnly
errors: errorCode

examples:
identify any anomalies in the AWS logs -> I cannot identify anomalies yet. I am still in training.
What actions did user Mike perform? ->fields @timestamp, userIdentity.userName, sourceIPAddress , eventName, @message | filter userIdentity.userName like "john" | sort @timestamp desc
Where did Helen log in to?->fields @timestamp, userIdentity.userName, sourceIPAddress , eventName, @message | filter userIdentity.userName like "helen" and eventName like "ConsoleLogin" | sort @timestamp desc
Where is Samy logging in from? ->fields @timestamp | filter userIdentity.userName like "Samy" and sourceIPAddress not like "AWS Internal" | sort @timestamp desc | stats count(*) as count by sourceIPAddress
What Ip Addresses is john using? ->fields @timestamp | filter userIdentity.userName like "Samy" and sourceIPAddress not like "AWS Internal" | stats count(*) as count by sourceIPAddress
What list commands did Bob do? ->fields @timestamp | filter userIdentity.userName like "bob" and eventName like "list" | stats count(*) as count by eventName
How many times did Larry execute a list command ->fields @timestamp | filter userIdentity.userName like "larry" and eventName like "list" | stats count(*) as count
What services did x interact with? ->fields @timestamp | filter userIdentity.userName like "x"  | stats count(*) as count by eventSource
Did Mike interact s3? ->fields @timestamp | filter userIdentity.userName like "mike" and eventSource like "s3"  | stats count(*) as count by eventSource
What buckets were accessed? ->fields @timestamp | filter eventSource like "s3" |stats count(*) as count by requestParameters.bucketName
What hosts communicated with 34.95.113.225? ->fields @timestamp | filter dstAddr like "34.95.113" | stats count(*) as count by @logStream, srcAddr, dstAddr, dstPort,action
What traffic was blocked going to 10.0? ->fields @timestamp | filter dstAddr like "10.0" and action not like "ACCEPT" | stats count(*) as count by @logStream, srcAddr, dstAddr, dstPort, action
What traffic was rejected going to 10.0 ? ->fields @timestamp | filter dstAddr like "10.0" and action not like "ACCEPT" | stats count(*) as count by @logStream, srcAddr, dstAddr, dstPort, action
What traffic was denied going to 10.0 ? ->fields @timestamp | filter dstAddr like "10.0" and action not like "ACCEPT" | stats count(*) as count by @logStream, srcAddr, dstAddr, dstPort, action
Who logged in last 24 hours? -> fields @timestamp, userIdentity.userName, sourceIPAddress , eventName, eventSource , @message | filter eventName like "ConsoleLogin" and sourceIPAddress not like "AWS Internal"
What are the last errors? - > fields @timestamp, errorCode, eventName, eventSource, @message, ispresent(errorCode) as errorCodePresent |filter errorCodePresent !=0
What network traffic ? ->fields @timestamp, @logStream, srcAddr, srcPort, dstAddr, dstPort,action,packets,@message  | filter @logStream like "eni"

instructions:
- use "=" instead of "like" for dstPort: example: "|filter dstport=80"
- only respond with a CloudWatch Logs Insights that starts with "fields"
- only use "stats count(*) as count by errorCode" when asked about statistics such as most, least, etc
- types of logs are log sources
- When asked about the most, use | sort count desc
- when asked about CloudTrail, use |filter @logStream like "CloudTrail", and use SourceIPAddress instead of srcAddr and show the following fields @timestamp, userIdentity.userName, sourceIPAddress , eventName, @message
- when asked about network traffic, use |filter @logStream like "eni"
- enumeration means events
- a select statement is somethign like "select * from"
- to an IP means that Ip is dstAddr
- When asked about a role, filter for userIdentity.arn
- logs with ssh service means network traffic on port 22
- events related to means search in @message
- Only respond with CloudWatch Logs Insights Query.

'''

B_SYS, E_SYS = "<|im_start|> system\n", "\n<|im_end|>\n\n"
B_USER, E_USER = "<|im_start|> user\n", "\n<|im_end|>\n\n"

def get_prompt(instruction, new_system_prompt=DEFAULT_SYSTEM_PROMPT ):
    SYSTEM_PROMPT = B_SYS + new_system_prompt + E_SYS
    prompt_template =  SYSTEM_PROMPT + B_USER+ instruction + E_USER
    return prompt_template

instruction = "{text}"
template = get_prompt(instruction)


def generate_response(input_qn):
  prompt = PromptTemplate(template=template, input_variables=["text"])
  llm_chain = LLMChain(prompt=prompt, llm=llm)

  response = llm_chain.run(input_qn)
  st.info(response)

#####################

with st.form('my_form'):
  input_text = st.text_area('Enter text:', 'what action did admin do?')

  submitted = st.form_submit_button('Submit')

  if submitted:
    generate_response(input_text)