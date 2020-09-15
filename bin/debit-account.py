#!/usr/bin/env python3
#
# Copyright Soramitsu Co., Ltd. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

# pip install iroha

import os
import binascii
import getopt
from iroha import IrohaCrypto
from iroha import Iroha, IrohaGrpc
from iroha.primitive_pb2 import can_set_my_account_detail
import pathlib
import sys
import uuid

if sys.version_info[0] < 3:
   raise Exception('Python 3 or a more recent version is required.')

HERE=pathlib.Path(__file__).parent.absolute().as_posix()
IROHA_CONFIG_KEY_PATH = os.getenv('IROHA_KEY_PATH', f"{str(HERE)}/../config/keys/")
IROHA_KEY_PATH = os.getenv('IROHA_KEY_PATH', f"{str(HERE)}/../keys/")
IROHA_HOST_ADDR = os.getenv('IROHA_HOST_ADDR', '127.0.0.1')
IROHA_PORT = os.getenv('IROHA_PORT', '50051')
ADMIN_ACCOUNT_ID = os.getenv('ADMIN_ACCOUNT_ID', 'admin@test')

admin_private_key_path = IROHA_CONFIG_KEY_PATH + ADMIN_ACCOUNT_ID + '.priv'
with open (admin_private_key_path, "r") as key_file:
   ADMIN_PRIVATE_KEY = ''.join(key_file.readlines())

iroha = Iroha(ADMIN_ACCOUNT_ID)
net = IrohaGrpc('{}:{}'.format(IROHA_HOST_ADDR, IROHA_PORT))

do_trace = False

def trace(func):
   """
   A decorator for tracing methods' begin/end execution points
   """

   def tracer(*args, **kwargs):
      name = func.__name__
      if do_trace and name != 'send_transaction_and_print_status':
        print('\tEntering "{}"'.format(name))
      result = func(*args, **kwargs)
      if do_trace and name != 'send_transaction_and_print_status':
        print('\tLeaving "{}"'.format(name) + '\n')
      return result

   return tracer


@trace
def send_transaction_and_print_status(transaction):
   hex_hash = binascii.hexlify(IrohaCrypto.hash(transaction))
   print('Transaction hash = {}, creator = {}'.format(
      hex_hash, transaction.payload.reduced_payload.creator_account_id))
   net.send_tx(transaction)
   for status in net.tx_status_stream(transaction):
      print(status)

@trace
def get_account_assets(account_id):
   """
   List all the assets of {account_id}@test
   """
   query = iroha.query('GetAccountAssets', account_id=account_id)
   IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

   response = net.send_query(query)
   return response.account_assets_response.account_assets

@trace
def get_account_details():
   """
   Get all the kv-storage entries for {account_id}@test
   """
   query = iroha.query('GetAccountDetail', account_id=f"{account_id}@test")
   IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

   response = net.send_query(query)
   return response.account_detail_response

@trace
def debit_account(account_id, amount, account_private_key):
   """
   Make admin@test able to set detail to {account_id}@test
   """
   print(f'Debiting ${amount} from {account_id}')

   account_assets = get_account_assets(account_id)
   asset_id = account_assets[0].asset_id #assuming only one asset

   tx = iroha.transaction([
      iroha.command('SubtractAssetQuantity', asset_id=asset_id, amount=amount)
   ], creator_account=account_id)
   IrohaCrypto.sign_transaction(tx, account_private_key)
   send_transaction_and_print_status(tx)

@trace
def get_account_assets(account_id):
   """
   List all the assets of {account_id}@test
   """
   query = iroha.query('GetAccountAssets', account_id=account_id)
   IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

   response = net.send_query(query)
   return response.account_assets_response.account_assets

def main(argv):
  amount = '10.00'
  account_id = None
  opts, args = getopt.getopt(argv,"q:a:",["quantity=","account="])
  for opt, arg in opts:
    if opt in ("-q", "--quantity"):
      amount = str(float(arg))
    elif opt in ("-a", "--account"):
      account_id = arg
  if account_id is None:
    print('Usage: debit-account.py (--account|-a) <account_id> [(--quantity|-q) <asset_quantity>]')
    print('  debit-account.py -c 4ecca3a2f1de11eaa9a8acde48001122@test -a 3.33')
    sys.exit()
  account_private_key_path = IROHA_KEY_PATH + account_id + '.priv'
  with open (account_private_key_path, "r") as key_file:
    account_private_key = ''.join(key_file.readlines())

  debit_account(account_id, amount, account_private_key)
  data = get_account_assets(account_id)
  if len(data) > 0:
    print(f'  {data[0].balance} {data[0].asset_id}') # will only have one asset

if __name__ == "__main__":
  main(sys.argv[1:])
