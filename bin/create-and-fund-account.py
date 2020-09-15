#!/usr/bin/env python3
#

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
IROHA_CONFIG_KEY_PATH = os.getenv('IROHA_KEY_PATH', f'{str(HERE)}/../config/keys/')
IROHA_KEY_PATH = os.getenv('IROHA_KEY_PATH', f'{str(HERE)}/../keys/')
IROHA_HOST_ADDR = os.getenv('IROHA_HOST_ADDR', '127.0.0.1')
IROHA_PORT = os.getenv('IROHA_PORT', '50051')
ADMIN_ACCOUNT_ID = os.getenv('ADMIN_ACCOUNT_ID', 'admin@test')

admin_private_key_path = IROHA_CONFIG_KEY_PATH + ADMIN_ACCOUNT_ID + '.priv'
with open (admin_private_key_path, "r") as key_file:
   ADMIN_PRIVATE_KEY = ''.join(key_file.readlines())

account_id = uuid.uuid1().hex  # because Iroha doesn't like "-" in its ids
account_private_key = None
account_public_key = None
account_private_key_path = f'{IROHA_KEY_PATH}{account_id}@test.priv'
if os.path.exists(account_private_key_path):
   with open (account_private_key_path, "w") as key_file:
      account_private_key = ''.join(key_file.readlines())
else:
   account_private_key = IrohaCrypto.private_key()
   with open (account_private_key_path, "w") as key_file:
      key_file.write(account_private_key.decode("ASCII"))

account_public_key_path = f'{IROHA_KEY_PATH}{account_id}@test.pub'
if os.path.exists(account_public_key_path):
   with open (account_public_key_path, "w") as key_file:
      account_public_key = ''.join(key_file.readlines())
else:
   account_public_key = IrohaCrypto.derive_public_key(account_private_key)
   with open (account_public_key_path, "w") as key_file:
      key_file.write(account_public_key.decode("ASCII"))

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
def create_funded_account(amount):
   """
   1. Create account f'{account_id}@test'
   2. Add {amount} units of 'coin#test' to 'admin@test'
   3. Transfer {amount} 'coin#test' from 'admin@test' to '{account_id}@test'
   """
   tx = iroha.transaction([
      iroha.command('CreateAccount', account_name=f'{account_id}', domain_id='test',
               public_key=account_public_key),
      iroha.command('AddAssetQuantity', asset_id='coin#test', amount=amount),
      iroha.command('TransferAsset', src_account_id=ADMIN_ACCOUNT_ID, dest_account_id=f'{account_id}@test',
               asset_id='coin#test', description='initial card funding', amount=amount)
   ])
   IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
   send_transaction_and_print_status(tx)

@trace
def card_grants_to_admin_set_account_detail_permission():
   """
   Make admin@test able to set detail to {account_id}@test
   """
   tx = iroha.transaction([
      iroha.command('GrantPermission', account_id=ADMIN_ACCOUNT_ID,
               permission=can_set_my_account_detail)
   ], creator_account=f'{account_id}@test')
   IrohaCrypto.sign_transaction(tx, account_private_key)
   send_transaction_and_print_status(tx)

@trace
def set_account_details(first_name, last_name, email):
   """
   Set first_name, last_name, email to {account_id}@test
      by admin@test
   """
   tx = iroha.transaction([
      iroha.command('SetAccountDetail',
               account_id=f'{account_id}@test', key='first_name', value=first_name),
      iroha.command('SetAccountDetail',
               account_id=f'{account_id}@test', key='last_name', value=last_name),
      iroha.command('SetAccountDetail',
               account_id=f'{account_id}@test', key='email', value=email)
   ])
   IrohaCrypto.sign_transaction(tx, ADMIN_PRIVATE_KEY)
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

@trace
def get_account_details():
   """
   Get all the kv-storage entries for {account_id}@test
   """
   query = iroha.query('GetAccountDetail', account_id=f'{account_id}@test')
   IrohaCrypto.sign_query(query, ADMIN_PRIVATE_KEY)

   response = net.send_query(query)
   return response.account_detail_response


def main(argv):
  amount = '10.00'
  opts, args = getopt.getopt(argv,"a:",["amount="])
  for opt, arg in opts:
    if opt in ("-a", "--amount"):
      amount = str(float(arg))

  create_funded_account(amount)

  data = get_account_details()
  print(f'Account: {account_id}@test')

  data = get_account_assets(f'{account_id}@test')
  if len(data) > 0:
    print(f'  {data[0].balance} {data[0].asset_id}') # will only have one asset

if __name__ == "__main__":
  main(sys.argv[1:])
