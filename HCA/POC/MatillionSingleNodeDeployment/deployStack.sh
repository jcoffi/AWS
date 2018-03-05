#!/bin/bash
echo "Deleting Stack"
aws cloudformation delete-stack --stack-name $1
aws cloudformation wait stack-delete-complete --stack-name $1
echo "Creating Stack"
aws cloudformation create-stack \
--stack-name "$1" \
--template-body "$(cat $2)" \
--parameters "$(cat $3)" \
--capabilities "CAPABILITY_IAM" > results.json
cat results.json
sed -i 's/StackId/StackName/g' results.json
aws cloudformation wait stack-create-complete --cli-input-json "$(cat ./results.json)"
aws cloudformation describe-stacks --cli-input-json "$(cat ./results.json)"
rm ./results.json
echo "Complete"
