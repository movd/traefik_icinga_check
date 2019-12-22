# traefik_icinga_check

Need a simple way to monitor web services exposed via Traefik v2 with Icinga2? This script should help. It will query your local Traefik REST API for all running routers (<del>frontends</del>). It fetches the exposed Routers with their coresponding hostnames and services (<del>backends</del>) and creates Icinga2 [apply rules](https://icinga.com/docs/icinga2/latest/doc/03-monitoring-basics/#apply-rules) that use the [HTTP check](https://icinga.com/docs/icinga2/latest/doc/10-icinga-template-library/#http). Run this script as cronjob so that new services that should be monitored are added automatically.

## Requirements

* A working Traefik v2.x reverse proxy with it's API exposed
* Icinga2 monitoring server

_I wrote a [blog post on upgrading Traefik v1 to v2](https://moritzvd.com/upgrade-traefik-2/) that also covers the set up of the API._

Before proceeding please make shure you can access Traefik's API. For example in this way:

```sh
curl -s --user admin:passw0rd http://example.lan:8080/api/http/routers | jq
[
  {
    "entryPoints": [
      "dashboard"
    ],
    "middlewares": [
      "dashboard-auth@file"
    ],
    ...
```
## Installation

Run all this steps on a Icinga 2 master or satellite node.

### Download script and install script

```sh
git clone https://github.com/movd/traefik_icinga_check
sudo -u nagios mkdir /etc/icinga2/cronjobs
chmod +x traefik_icinga_check/traefik2_to_icinga.py
sudo cp traefik_icinga_check/traefik2_to_icinga.py  /etc/icinga2/cronjobs/
sudo chown nagios:nagios /etc/icinga2/cronjobs/traefik2_to_icinga.py
```
### Set up parameters via .env

```sh
$ sudo -u nagios touch /etc/icinga2/cronjobs/.env
```
Open and insert parameters `/etc/icinga2/cronjobs/.env` (same as Traefik dashboard)

```sh
TRAEFIK_API_HOSTNAME='example.lan:8000'
TRAEFIK_USERNAME='admin'
TRAEFIK_PASSWORD='passw0rd'
```

### Test the script manually by printing to STDOUT

```sh
$ sudo -u nagios /etc/icinga2/cronjobs/traefik2_to_icinga.py
apply Service "example.com https apache-apache" {
                import "generic-service"
                check_command = "http"
                vars.http_address = "example.com"
                vars.http_vhost = "example.com"

                vars.http_ssl = "1"
                vars.http_sni = "true"

                vars.notification["mail"] = {
                    groups = [ "icingaadmins" ]
                }
...
```

### Configure the Host that runs Traefik

Edit your Traefik host and add the `vars.services` array, so that it matches the rules set in `traefik2_to_icinga.py`

```sh
object Host "Reverse Proxy" {
  import "generic-host"
  address = "10.0.0.254"
  vars.os = "Linux" 
  vars.services = ["traefik"]
}
```

### Create cronjob for `nagios` user

```sh
sudo -u nagios crontab -e
```
Edit and insert nightly cronjob. Something like that should suffice.

```sh
# Daily at 2am: Generate Icinga checks from Traefik API and restart Icinga2 service
0 2 * * * /etc/icinga2/cronjobs/traefik2_to_icinga.py > /etc/icinga2/zones.d/YOUR-ZONE/traefik_services.conf && systemctl restart icinga2 >/dev/null 2>&1
```
_Note:_ Of course you need to print the output of `traefik2_to_icinga.py` to a directory that is either inside your zone or in conf.d








