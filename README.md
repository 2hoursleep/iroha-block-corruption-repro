Hyperledger Iroha blockchain immutability failure repro
====

This is an isolated repro of an issue I experienced with Iroha 1.1.3 where
I was able to corrupt a block, giving an account "more money", without Iroha
complaining or failing to start.

## Dependencies
This repro was developed on a Mac, but it should be portable to linux.
  - bash
  - docker
  - docker-compose
  - python3
    - with `iroha` module

## Repro steps
From this root of this project, do the following:

### 1. Spin up Iroha
```
./bin/setup.sh
```

### 2. Add 10.00 asset quantity to a new account, saving the account_id
```
ACCOUNT=$(./bin/create-and-fund-account.py | grep Account | sed 's/Account: //')
```

### 3. Subtract from the asset quantity
```
./bin/debit-account.py -a ${ACCOUNT} -q 1.00
```
At this point you get the expected `9.00` quantity.

### 4. Poison the blockchain by modifying the block that adds and transfers asset quantity
Change `10.00` to `100.00`
```
sed -i'.bak' 's/10\.00/100.00/g' ./volumes/blockstore/0000000000000002
rm -f ./volumes/blockstore/0000000000000002.bak
```

### 5. Subtract from the asset quantity again
```
./bin/debit-account.py -a ${ACCOUNT} -q 1.00
```
At this point you get the expected `8.00` quantity, before the node is restarted.

### 6. Drop and re-add the node
```
docker stop iroha
docker rm iroha
docker-compose -f ./docker/docker-compose.yml up -d
```
Strangely enough, merely restarting the node does not repro the issue. It requires
actually removing the node and adding it back to trigger it.

### 7. Subtract from the asset quantity once again
```
./bin/debit-account.py -a ${ACCOUNT} -q 1.00
```
At this point, you will get `97.00` quantity, which is not expected.
