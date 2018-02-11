scss ?= static/scss/main.scss
css ?= static/css/main.css

all: styles

staging:
	cd deploy/ && fab deploy --set environment=staging && cd ..

production:
	cd deploy/ && fab deploy --set environment=production && cd ..

# standalone push, don't download data (assume it's present)
# suitable for automatic deploy from an unattended server
# uses credentials from the "scan-box-deployer" service
cg_production_autodeploy:
	cf login -a $$CF_API -u $$CF_USERNAME -p $$CF_PASSWORD -o gsa-ogp-pulse -s pulse && cf push pulse

# download data externally and then deploy to production
cg_production:
	make data_init && cf target -o gsa-ogp-pulse -s pulse && cf push pulse

cg_staging:
	make data_init && cf target -o gsa-ogp-pulse -s pulse && cf push pulse-staging

debug:
	DEBUG=true python pulse.py

styles:
	sass $(scss):$(css)

watch:
	sass --watch $(scss):$(css)

clean:
	rm -f $(css)

# Production data update process:
#
# Run a fresh scan, update the database, and upload data to S3.
# Enable Lambda mode, using Lambda AWS profile set up in production.
update_production:
	python -m data.update --scan=here --upload --lambda --lambda-profile=lambda

# Staging data update process:
#
# Download last production scan data, update the database.
update_staging:
	python -m data.update --scan=download

# Development data update process:
#
# Don't scan or download latest data (rely on local cache), update database.
update_development:
	python -m data.update --scan=skip

# downloads latest snapshot of data locally
# Pending cloud.gov production bucket:
# cg-4adefb86-dadb-4ecf-be3e-f1c7b4f6d084
# Pending cloud.gov backup bucket:
# cg-72ce4caf-d81b-4771-9b96-3624b5554587
data_init:
	python -m data.update --just-download

#
# https.jetzt additions:
#

deploy.sh:
	wget -O ./deploy.sh https://raw.githubusercontent.com/X1011/git-directory-deploy/e37ac94cda4bfc5773c0f01d89d8c875a21ab4f9/deploy.sh
	chmod +x ./deploy.sh

publish: deploy.sh
	rm -rf build || true
	mkdir -p build
	python3 freeze.py
	echo "https-norge.byeskille.no" > build/CNAME
	GIT_DEPLOY_DIR=build GIT_DEPLOY_BRANCH=static-pages-norway GIT_DEPLOY_REPO=git@github.com:byeskille/pulse.git ./deploy.sh -m "static build" -n

update_httpsjetzt:
	pip3 install --user -r requirements.txt
	mkdir -p data/output/subdomains/gather/results
	touch data/output/subdomains/gather/results/gathered.csv
	DOMAIN_SCAN_PATH="../domain-scan/scan" SCANNERS=pshtt,sslyze python3 -m data.update --scan=here --gather=skip --lambda
