# amxbpm-py-utils
AMX BPM Utils
=============

appStatus - Use SOAP API to connect to Admin and get list of applications, versions and status
appRemove - Connect to Admin and get list of DAAs used and unused, allows deleteion of unused DAAs
analyse   - Analyse BPM log file and get number of rest transactions
appHalted - Show list of halted instances, do a retry if flag set (BPM REST)


 ./ansible contains scripts for updating the py files to the host machines using git 

For production ex.

nsb_hosts.ini : all NSB hosts
cdn_hosts.ini : all CDN hosts except PROD

 ansible-playbook -i nsb_hosts.ini upload.yml --extra-vars "target=prod"
