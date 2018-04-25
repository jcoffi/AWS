
#!/bin/bash -xe
yum update -y aws-cfn-bootstrap
yum install -y awslogs xmlstarlet openldap-clients-2.4.40-12.30.amzn1.x86_64
StackName='myStack'
Region='us-west-2'
RealmConName='svc-matillion@corp.int'
RealmConPass='NiceTry.Thisisnotthepassword.'
RealmConURL='ldap://10.0.1.193:389'
RealmRoleBase='OU=Matillion,OU=Roles,DC=corp,DC=int'
RealmRoleName='cn'
RealmRoleSearch='member={0}'
RealmUserBase='CN=Users,DC=corp,DC=int'
RealmUserSearch='sAMAccountName={0}'
service awslogs start
sudo chkconfig awslogs on
/opt/aws/bin/cfn-init --stack $StackName --resource Ec2Instance0 --region $Region
xmlstarlet ed --inplace -d "/Server/Service/Engine/Realm"\
-s '/Server/Service/Engine' -t elem -n Realm -v ""\
-i '/Server/Service/Engine/Realm' -t attr -n className -v org.apache.catalina.realm.JNDIRealm\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n connectionName -v $RealmConName\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n connectionPassword -v '$RealmConPass'\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n connectionURL -v $RealmConURL\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n roleBase -v $RealmRoleBase\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n roleName -v $RealmRoleName\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n roleSearch -v $RealmRoleSearch\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n userBase -v $RealmUserBase\
-i '/Server/Service/Engine/Realm[@className=\"org.apache.catalina.realm.JNDIRealm\"]' -t attr -n userSearch -v $RealmUserSearch\
/etc/tomcat8/server.xml

cp /usr/share/emerald/WEB-INF/security.fragment.enabled /usr/share/emerald/WEB-INF/security.fragment
sed -i -e "s/\(<role-name>\)\([[:alnum:]]\+\?\)\(<\/role-name>\)/\1$RealmMETLRole \3/g" /usr/share/emerald/WEB-INF/security.fragment
sed -i '/^ADMIN_ROLE_NAME=/{h;s/=.*/=$RealmMETLAdminRole/};${x;/^$/{s//ADMIN_ROLE_NAME=$RealmMETLAdminRole/;H};x}' /usr/share/emerald/WEB-INF/classes/Emerald.properties
sed -i '/^API_SECURITY_GROUP=/{h;s/=.*/=$RealmMETLAPIRole/};${x;/^$/{s//API_SECURITY_GROUP=$RealmMETLAPIRole/;H};x}' /usr/share/emerald/WEB-INF/classes/Emerald.properties
