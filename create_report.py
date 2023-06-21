'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Jun 21 2023
File : create_report.py
'''
import sys, os, logging, argparse, json, re
from datetime import datetime

import _version
import report_data
import report_artifacts
import report_errors


###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 7):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.10.5. ")
else:
    pass

propertiesFile = "../server_properties.json"  # Created by installer or manually
propertiesFile = logfileName = os.path.dirname(os.path.realpath(__file__)) + "/" +  propertiesFile
logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_project_inventory_license_audit_report.log"

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module


####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-pid', "--projectID", help="Project ID")
parser.add_argument("-rid", "--reportID", help="Report ID")
parser.add_argument("-authToken", "--authToken", help="Code Insight Authorization Token")
parser.add_argument("-baseURL", "--baseURL", help="Code Insight Core Server Protocol/Domain Name/Port.  i.e. http://localhost:8888 or https://sca.codeinsight.com:8443")
parser.add_argument("-reportOpts", "--reportOptions", help="Options for report content")

#----------------------------------------------------------------------#
def main():

    reportName = "Project Inventory License Audit Report"
    auditField = "License"

    logger.info("Creating %s - %s" %(reportName, _version.__version__))
    print("Creating %s - %s" %(reportName, _version.__version__))
    print("    Logfile: %s" %(logfileName))

    #####################################################################################################
    #  Code Insight System Information
    #  Pull the base URL from the same file that the installer is creating
    if os.path.exists(propertiesFile):
        try:
            file_ptr = open(propertiesFile, "r")
            configData = json.load(file_ptr)
            baseURL = configData["core.server.url"]
            file_ptr.close()
            logger.info("Using baseURL from properties file: %s" %propertiesFile)
        except:
            logger.error("Unable to open properties file: %s" %propertiesFile)

        # Is there a self signed certificate to consider?
        try:
            certificatePath = configData["core.server.certificate"]
            os.environ["REQUESTS_CA_BUNDLE"] = certificatePath
            os.environ["SSL_CERT_FILE"] = certificatePath
            logger.info("Self signed certificate added to env")
        except:
            logger.info("No self signed certificate in properties file")
    else:
        baseURL = "http://localhost:8888"   # Required if the core.server.properties files is not used
        logger.info("Using baseURL from create_report.py")

    # See what if any arguments were provided
    args = parser.parse_args()
    projectID = args.projectID
    reportID = args.reportID
    authToken = args.authToken
    reportOptions = args.reportOptions

    # Based on how the shell pass the arguemnts clean up the options if on a linux system:w
    if sys.platform.startswith('linux'):
        reportOptions = reportOptions.replace('""', '"')[1:-1]

    reportOptions = json.loads(reportOptions)
    reportOptions = verifyOptions(reportOptions) 

    logger.debug("Custom Report Provided Arguments:")	
    logger.debug("    projectID:  %s" %projectID)	
    logger.debug("    reportID:   %s" %reportID)	
    logger.debug("    baseURL:  %s" %baseURL)	
    logger.debug("    reportOptions:  %s" %reportOptions)	

    fileNameTimeStamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if "errorMsg" in reportOptions.keys():

        reportFileNameBase = reportName.replace(" ", "_") + "-Creation_Error-" + fileNameTimeStamp
        
        reportData = {}
        reportData["errorMsg"] = reportOptions["errorMsg"]
        reportData["reportName"] = reportName
        reportData["reportTimeStamp"] = datetime.strptime(fileNameTimeStamp, "%Y%m%d-%H%M%S").strftime("%B %d, %Y at %H:%M:%S")
        reportData["reportFileNameBase"] = reportFileNameBase
        
        reports = report_errors.create_error_report(reportData)
        print("    *** ERROR  ***  Error found validating report options")
    else:
        reportData = report_data.gather_data_for_report(baseURL, projectID, authToken, reportName, reportOptions, auditField)
        print("    Report data has been collected")
        projectName = reportData["projectName"]
        projectNameForFile = re.sub(r"[^a-zA-Z0-9]+", '-', projectName )  # Remove special characters from project name for artifacts
        
        # Are there child projects involved?  If so have the artifact file names reflect this fact
        if len(reportData["projectList"])==1:
            reportFileNameBase = projectNameForFile + "-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp
        else:
            reportFileNameBase = projectNameForFile + "-with-children-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp

        reportData["fileNameTimeStamp"] = fileNameTimeStamp
        reportData["reportTimeStamp"] = datetime.strptime(fileNameTimeStamp, "%Y%m%d-%H%M%S").strftime("%B %d, %Y at %H:%M:%S")
        reportData["reportFileNameBase"] = reportFileNameBase

        # Was there any errors while collection the report data?
        if "errorMsg" in reportData.keys():
            reports = report_errors.create_error_report(reportData)
            print("    Error report artifacts have been created")
        else:
            reports = report_artifacts.create_report_artifacts(reportData)
            print("    Report artifacts have been created")


#----------------------------------------------------------------------# 
def verifyOptions(reportOptions):
	'''
	Expected Options for report:
		includeChildProjects - True/False
	'''
	reportOptions["errorMsg"] = []
	trueOptions = ["true", "t", "yes", "y"]
	falseOptions = ["false", "f", "no", "n"]

	includeChildProjects = reportOptions["includeChildProjects"]

	if includeChildProjects.lower() in trueOptions:
		reportOptions["includeChildProjects"] = True
	elif includeChildProjects.lower() in falseOptions:
		reportOptions["includeChildProjects"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including child projects: <b>%s</b>.  Valid options are <b>True/False</b>" %includeChildProjects)
    

	if not reportOptions["errorMsg"]:
		reportOptions.pop('errorMsg', None)

	return reportOptions


        
#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  