from openai import OpenAI

from config import MODEL_NAME
client = OpenAI(api_key="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")

# res = client.files.create(
#   file=open("model.jsonl", "rb"),
#   purpose="fine-tune"
# )

# print(res)

# res_file = client.files.list()
# print(res_file)

# res_model_train = client.fine_tuning.jobs.create(
#   training_file="file-5EuIMfT09Tm5IHbZBPyx80x2", 
#   model=MODEL_NAME
# )

# print(res_model_train)

# ftjob-D6IAm4X0eVmez7clISUNcrXv

print(client.fine_tuning.jobs.retrieve("ftjob-D6IAm4X0eVmez7clISUNcrXv"))