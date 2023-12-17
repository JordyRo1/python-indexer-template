import logging

from apibara.indexer import IndexerRunner, IndexerRunnerConfiguration, Info
from apibara.indexer.indexer import IndexerConfiguration
from apibara.protocol.proto.stream_pb2 import Cursor, DataFinality
from apibara.starknet import EventFilter, Filter, StarkNetIndexer, felt, TransactionFilter
from apibara.starknet.cursor import starknet_cursor
from apibara.starknet.proto.starknet_pb2 import Block
from pymongo import MongoClient
from dotenv import load_dotenv
import os 


load_dotenv()


# Print apibara logs
root_logger = logging.getLogger("apibara")
# change to `logging.DEBUG` to print more information
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())

randomness_address = felt.from_hex(
    "0x71659c6e691800b9f0d700ea5a96f0dd8f8c5bcf13d91c045853b3699cc7d45"
)

# `Transfer` selector.
# You can get this value either with starknet.py's `ContractFunction.get_selector`
# or from starkscan.
transfer_key = felt.from_hex(
    "0x8a1691d2b9d5e93bc2e52eae31be1c5ace6a80c2a45b3e7e77a64a11f22ecb"
)

# tx_hash = felt.from_hex(
#     "0xd52dbd0fb027286fa0e116d9f20f71da4a236168d8e56dd6db45c72c984f50"
# )



class RandomnessIndexer(StarkNetIndexer):
    def __init__(self):
        super().__init__() 
        # Initialize MongoDB Client
        self.client = MongoClient(os.getenv("MONGODB_URL"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.collection = self.db[os.getenv("COLLECTION_NAME")]

    def indexer_id(self) -> str:
        return "randomness_indexer"

    def initial_configuration(self) -> Filter:
        # Return initial configuration of the indexer.
        return IndexerConfiguration(
            filter=Filter().add_event(
                EventFilter().with_from_address(randomness_address).with_keys([transfer_key])
            ),
            starting_cursor=starknet_cursor(7000),
            finality=DataFinality.DATA_STATUS_ACCEPTED,
        )

    async def handle_data(self, info: Info, data: Block):
        # Handle one block of data
        for event_with_tx in data.events:
            tx_hash = felt.to_hex(event_with_tx.transaction.meta.hash)
            event = event_with_tx.event
            document = {"tx_hash": tx_hash, 
                        "request_id": felt.to_hex(event.data[0]),
                        "requestor_address": felt.to_hex(event.data[1]),
                        "seed": hex(felt.to_int(event.data[2])),
                        "minimum_block_number": hex(felt.to_int(event.data[3])),
                        "random_words": hex(felt.to_int(event.data[5])),
                        "proof": [hex(felt.to_int(event.data[7])),hex(felt.to_int(event.data[8])), hex(felt.to_int(event.data[9]))]
                        }
            self.collection.insert_one(document)
            print(document)
    
    async def handle_invalidate(self, _info: Info, _cursor: Cursor):
        raise ValueError("data must be finalized")


async def run_indexer(server_url=None, mongo_url=None, restart=None, dna_token=None):
    runner = IndexerRunner(
        config=IndexerRunnerConfiguration(
            stream_url=server_url,
            storage_url=mongo_url,
            token=dna_token,
        ),
        reset_state=restart,
    )
    # ctx can be accessed by the callbacks in `info`.
    await runner.run(RandomnessIndexer(), ctx={"network": "starknet-sepolia"})
