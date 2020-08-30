from omniscope.api import OmniscopeApi
import pandas as pd
import etherscan

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
apikey = omniscope_api.get_option("apikey")

address = omniscope_api.get_option("address")
addresses = input_data[address].tolist()

es = etherscan.Client(
    api_key=apikey,
    cache_expire_after=5,
)

method = omniscope_api.get_option("method")
output_data = None

if method == "get_eth_balance" :
    eth_balance = es.get_eth_balance(addresses[0])
    output_data = pd.DataFrame({'ETH Balance':[eth_balance]})
elif method == "get_eth_balances" :
    for i in range(0, len(addresses), 20):
        chunk = addresses[i:i + 20]
        eth_balance = es.get_eth_balances(chunk)
        df = pd.DataFrame(list(eth_balance.items()),
                      columns=['Account','Balance'])
        if output_data is None:
            output_data = df
        else:
            output_data = pd.concat([output_data, df])

else :
    for i in range(0, len(addresses)):
        eth_transactions = es.get_transactions_by_address(addresses[i])
        df = pd.json_normalize(eth_transactions)
        if output_data is None:
            output_data = df
        else:
            output_data = pd.concat([output_data, df])

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()