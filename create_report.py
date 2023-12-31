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
import zipfile

import _version
import report_data
import report_artifacts
import report_errors
import CodeInsight_RESTAPIs.project.upload_reports

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 6):
    raise Exception("The current version of Python is less than 3.6 which is unsupported.\n Script created/tested against python version 3.6.8. ")
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

    print("    Create report archive for upload")
    uploadZipfile = create_report_zipfile(reports, reportFileNameBase)
    print("    Upload zip file creation completed")


    #########################################################
    # Upload the file to Code Insight
    CodeInsight_RESTAPIs.project.upload_reports.upload_project_report_data(baseURL, projectID, reportID, authToken, uploadZipfile)



#----------------------------------------------------------------------# 
def verifyOptions(reportOptions):
    '''
    Expected Options for report:
        includeChildProjects - True/False
        onlyRestrictedLicenses - True/False
    '''
    reportOptions["errorMsg"] = []
    trueOptions = ["true", "t", "yes", "y"]
    falseOptions = ["false", "f", "no", "n"]

    includeChildProjects = reportOptions["includeChildProjects"]
    restrictedLicensesOnly = reportOptions["restrictedLicensesOnly"]

    if includeChildProjects.lower() in trueOptions:
        reportOptions["includeChildProjects"] = True
    elif includeChildProjects.lower() in falseOptions:
        reportOptions["includeChildProjects"] = False
    else:
        reportOptions["errorMsg"].append("Invalid option for including child projects: <b>%s</b>.  Valid options are <b>True/False</b>" %includeChildProjects)

    if restrictedLicensesOnly.lower() in trueOptions:
        reportOptions["restrictedLicensesOnly"] = True
    elif restrictedLicensesOnly.lower() in falseOptions:
        reportOptions["restrictedLicensesOnly"] = False
    else:
        reportOptions["errorMsg"].append("Invalid option for restricted license option: <b>%s</b>.  Valid options are <b>True/False</b>" %restrictedLicensesOnly)

    if not reportOptions["errorMsg"]:
        reportOptions.pop('errorMsg', None)

    return reportOptions

#---------------------------------------------------------------------#
def create_report_zipfile(reportOutputs, reportFileNameBase):
	logger.info("Entering create_report_zipfile")
	allFormatZipFile = reportFileNameBase + ".zip"

	# create a ZipFile object
	allFormatsZip = zipfile.ZipFile(allFormatZipFile, 'w', zipfile.ZIP_DEFLATED)

	logger.debug("    Create downloadable archive: %s" %allFormatZipFile)
	print("    Create downloadable archive: %s" %allFormatZipFile)
	for format in reportOutputs["allFormats"]:
		print("        Adding %s to zip" %format)
		logger.debug("        Adding %s to zip" %format)
		allFormatsZip.write(format)

	allFormatsZip.close()
	logger.debug("    Downloadable archive created")
	print("    Downloadable archive created")

	# Now create a temp zipfile of the zipfile along with the viewable file itself
	uploadZipflle = allFormatZipFile.replace(".zip", "_upload.zip")
	print("    Create zip archive containing viewable and downloadable archive for upload: %s" %uploadZipflle)
	logger.debug("    Create zip archive containing viewable and downloadable archive for upload: %s" %uploadZipflle)
	zipToUpload = zipfile.ZipFile(uploadZipflle, 'w', zipfile.ZIP_DEFLATED)
	zipToUpload.write(reportOutputs["viewable"])
	zipToUpload.write(allFormatZipFile)
	zipToUpload.close()
	logger.debug("    Archive zip file for upload has been created")
	print("        Archive zip file for upload has been created")

	# Clean up the items that were added to the zipfile
	try:
		os.remove(allFormatZipFile)
	except OSError:
		logger.error("Error removing %s" %allFormatZipFile)
		print("Error removing %s" %allFormatZipFile)
		return -1

	for fileName in reportOutputs["allFormats"]:
		try:
			os.remove(fileName)
		except OSError:
			logger.error("Error removing %s" %fileName)
			print("Error removing %s" %fileName)
			return -1    

	logger.info("Exiting create_report_zipfile")
	return uploadZipflle

        
#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  