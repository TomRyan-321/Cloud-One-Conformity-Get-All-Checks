import os
import json
import requests
import csv


def get_account_ids():
    accountsapi = f"https://{CC_REGION}-api.cloudconformity.com/v1/accounts"
    r = session.get(accountsapi, headers=headers).json()
    accounts = [account["id"] for account in r["data"]]
    return ",".join(accounts)


def get_checks():
    print("Querying checks API for the following accounts:", CC_ACCOUNTIDS)
    # Pagination variables
    CC_PAGESIZE = 1000
    CC_PAGENUMBER = 0
    checksapi = f"https://{CC_REGION}-api.cloudconformity.com/v1/checks"
    checkparams = {
        "accountIds": CC_ACCOUNTIDS,
        "filter[categories]": os.environ.get(
            "CC_FILTER_CATEGORIES", "cost-optimisation"
        ),
        "filter[compliances]": os.environ.get("CC_FILTER_COMPLIANCES", ""),
        "filter[createdLessThanDays]": os.environ.get("CC_FILTER_CREATEDLESSTHAN", ""),
        "filter[createdMoreThanDays]": os.environ.get("CC_FILTER_CREATEDMORETHAN", ""),
        "filter[newerThanDays]": os.environ.get("CC_FILTER_NEWERTHANDAYS", ""),
        "filter[olderThanDays]": os.environ.get("CC_FILTER_OLDERTHANDAYS", ""),
        "filter[regions]": os.environ.get("CC_FILTER_REGIONS", ""),
        "filter[resource]": os.environ.get("CC_FILTER_RESOURCE", ""),
        "filter[riskLevels]": os.environ.get("CC_FILTER_RISKLEVELS", ""),
        "filter[ruleIds]": os.environ.get("CC_FILTER_RULEIDS", ""),
        "filter[services]": os.environ.get("CC_FILTER_SERVICES", ""),
        "filter[statuses]": os.environ.get("CC_FILTER_STATUSES", "FAILURE"),
        "filter[tags]": os.environ.get("CC_FILTER_TAGS", ""),
        "page[size]": CC_PAGESIZE,
        "page[number]": CC_PAGENUMBER,
    }
    combined = []
    counter = 0
    max_results = 1
    while counter <= max_results:
        page = session.get(checksapi, params=checkparams, headers=headers).json()
        max_results = page["meta"]["total"]
        counter += CC_PAGESIZE
        checkparams["page[number]"] += 1
        data = page["data"]
        combined += data
    return {"data": combined, "meta": page["meta"]}


def create_csv():
    response_json = get_checks()
    if response_json["meta"]["total"] > 10000:
        raise Exception(
            "Maximum number of results for Checks API exceeded (10000), please limit results by including additional filters or limiting number of accounts queried using the CC_ACCOUNTIDS environment variable"
        )
    else:
        with open("wastage.csv", mode="w") as wastage_file:
            print("Creating CSV File")
            wastage_writer = csv.writer(
                wastage_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            wastage_writer.writerow(
                [
                    "AccountId",
                    "RuleId",
                    "Message",
                    "Resource",
                    "ResourceType",
                    "Cost",
                    "Wastage",
                ]
            )
            for check in response_json["data"]:
                if check["attributes"]["waste"] > 0:
                    wastage_writer.writerow(
                        [
                            check["relationships"]["account"]["data"]["id"],
                            check["relationships"]["rule"]["data"]["id"],
                            check["attributes"]["message"],
                            check["attributes"]["resource"],
                            check["attributes"]["resourceName"],
                            check["attributes"]["cost"],
                            check["attributes"]["waste"],
                        ]
                    )
            print("Successfully created:", wastage_file.name)
            wastage_file.close()


session = requests.session()

# Conformity Region, API Key & Target Account(s) variables
print("Checking whether variables set")
try:
    CC_APIKEY = os.environ["CC_APIKEY"]
    print("CC_APIKEY is set")
except:
    raise Exception(
        "No API Key Set, please set the CC_APIKEY environment variable with your API Key"
    )
headers = {
    "Content-Type": "application/vnd.api+json",
    "Authorization": "ApiKey " + CC_APIKEY,
}

try:
    CC_REGION = os.environ["CC_REGION"]
    print("CC_REGION variable is set with =", CC_REGION)
except:
    CC_REGION = "us-west-2"
    print("CC_REGION variable is not set, using default value of us-west-2")

try:
    CC_ACCOUNTIDS = os.environ["CC_ACCOUNTIDS"]
    print("CC_ACCOUNTIDS variable set with =", CC_ACCOUNTIDS)
except:  # Get All Account IDs
    print("CC_ACCOUNTIDS environment variable not set, getting all account ids")
    CC_ACCOUNTIDS = get_account_ids()

create_csv()
