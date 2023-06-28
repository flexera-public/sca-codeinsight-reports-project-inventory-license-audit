'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Jun 21 2023
File : report_data.py
'''
import logging
import restricted_licenses

import CodeInsight_RESTAPIs.project.get_child_projects
import CodeInsight_RESTAPIs.project.get_inventory_summary
import CodeInsight_RESTAPIs.project.get_project_information
import CodeInsight_RESTAPIs.inventory.get_inventory_history
import CodeInsight_RESTAPIs.license.license_lookup


logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module



#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportName, reportOptions, auditField):
    logger.info("Entering gather_data_for_report")

    # Parse report options
    includeChildProjects = reportOptions["includeChildProjects"]  # True/False
    restrictedLicensesOnly = reportOptions["onlyRestrictedLicenses"]  # True/False

    projectList = [] # List to hold parent/child details for report
    projectData = {} # Create a dictionary containing the project level summary data using projectID as keys
    auditHistory = {} # Hold the event data for a specific inventory Item
    applicationDetails = {} # Dictionary to allow a project to be mapped to an application name/version
    licenseMappings = {} # Allow to make a license name to a given license ID

    # Get the list of parent/child projects start at the base project
    projectHierarchy = CodeInsight_RESTAPIs.project.get_child_projects.get_child_projects_recursively(baseURL, projectID, authToken)

    # Create a list of project data sorted by the project name at each level for report display  
    # Add details for the parent node
    nodeDetails = {}
    nodeDetails["parent"] = "#"  # The root node
    nodeDetails["projectName"] = projectHierarchy["name"]
    nodeDetails["projectID"] = projectHierarchy["id"]
    nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectHierarchy["id"]) + "&tab=projectInventory"

    projectList.append(nodeDetails)

    if includeChildProjects:
        projectList = create_project_hierarchy(projectHierarchy, projectHierarchy["id"], projectList, baseURL)
    else:
        logger.debug("Child hierarchy disabled")

    #  Gather the details for each project and summerize the data
    for project in projectList:

        projectID = project["projectID"]
        projectName = project["projectName"]
        projectLink = project["projectLink"]

        applicationDetails[projectName] = determine_application_details(baseURL, projectName, projectID, authToken)
        applicationNameVersion = applicationDetails[projectName]["applicationNameVersion"]
        
        # Add the applicationNameVersion to the project hierarchy
        project["applicationNameVersion"] = applicationNameVersion
        
        projectInventorySummary = CodeInsight_RESTAPIs.project.get_inventory_summary.get_project_inventory_without_vulns_summary(baseURL, projectID, authToken)

        if not projectInventorySummary:
            logger.warning("    Project contains no inventory items")
            print("Project contains no inventory items.")

        # Create empty dictionary for project level data for this project
        projectData[projectName] = {}

        currentItem=0

        for inventoryItem in projectInventorySummary:

            # This is not a component for move to the next item
            if inventoryItem["type"] != "Component":
                continue
           
            currentItem +=1
            reportableEvent = False # only make true if there is an event we want to track
            inventoryAuditHistory = {}

            inventoryID = inventoryItem["id"]
            inventoryItemName = inventoryItem["name"]

            logger.debug("Processing inventory items %s of %s" %(currentItem, len(projectInventorySummary)))
            logger.debug("    Project:  %s   Inventory Name: %s  Inventory ID: %s" %(projectName, inventoryItemName, inventoryID))

            # Get the inventory history for this item
            inventoryHistory = CodeInsight_RESTAPIs.inventory.get_inventory_history.get_inventory_history_details(baseURL, inventoryID, authToken)
            for eventID in inventoryHistory:
                inventoryChangeEvent = inventoryHistory[eventID]
        
                for action in inventoryChangeEvent:
                    if auditField in action["field"]:

                        if restrictedLicensesOnly and action["oldValue"] in restricted_licenses.restrictedLicenses or not restrictedLicensesOnly:

                            # since this is an event we care about we need to capture the details for this inventory item
                            reportableEvent = True
                            inventoryAuditHistory[eventID] = {}
                            inventoryAuditHistory[eventID]["date"] = action["date"]
                            inventoryAuditHistory[eventID]["user"] = action["user"]
                            inventoryAuditHistory[eventID]["userEmail"] = action["userEmail"]
                            
                            # Specific for license events we need to map the license IDs to license names
                            oldLicenseID  = action["oldValue"]
                            newLicenseID = action["newValue"]

                            # Is there a mapping for the old license ID?
                            if oldLicenseID in licenseMappings:
                                licenseName = licenseMappings[oldLicenseID]
                            else:
                                licenseDetails = CodeInsight_RESTAPIs.license.license_lookup.get_license_details(baseURL, oldLicenseID, authToken) 

                                spdxIdentifier = licenseDetails["spdxIdentifier"]
                                if spdxIdentifier != "" and spdxIdentifier != "N/A":
                                    licenseName = spdxIdentifier
                                else:
                                    licenseName = licenseDetails["shortName"]
                                    licenseMappings[oldLicenseID] = licenseName
                            
                            inventoryAuditHistory[eventID]["oldValue"] = licenseName       

                            # Is there a mapping for the new license ID?
                            if newLicenseID in licenseMappings:
                                licenseName= licenseMappings[newLicenseID]
                            else:
                                licenseDetails = CodeInsight_RESTAPIs.license.license_lookup.get_license_details(baseURL, newLicenseID, authToken) 

                                spdxIdentifier = licenseDetails["spdxIdentifier"]
                                if spdxIdentifier != "" and spdxIdentifier != "N/A":
                                    licenseName = spdxIdentifier
                                else:
                                    licenseName = licenseDetails["shortName"]   
                                    licenseMappings[newLicenseID] = licenseName 
                            
                            inventoryAuditHistory[eventID]["newValue"] = licenseName    

            # Was there at least one licnse change for this inventory item>
            if reportableEvent:

                auditHistory[inventoryID] = {}
                auditHistory[inventoryID]["inventoryItemName"] = inventoryItemName
                auditHistory[inventoryID]["inventoryItemLink"] = baseURL + '''/codeinsight/FNCI#myprojectdetails/?id=''' + str(projectID) + '''&tab=projectInventory&pinv=''' + str(inventoryID)

                auditHistory[inventoryID]["project"] = projectName
                auditHistory[inventoryID]["projectLink"] = projectLink
                auditHistory[inventoryID]["events"] = inventoryAuditHistory

    # Build up the data to return for the
    reportData = {}
    reportData["reportName"] = reportName
    reportData["projectList"] = projectList
    reportData["projectHierarchy"] = projectHierarchy
    reportData["projectName"] = projectHierarchy["name"]
    reportData["auditHistory"] = auditHistory

    return reportData


#----------------------------------------------#
def create_project_hierarchy(project, parentID, projectList, baseURL):
    logger.debug("Entering create_project_hierarchy.")
    logger.debug("    Project Details: %s" %project)

    # Are there more child projects for this project?
    if len(project["childProject"]):

        # Sort by project name of child projects
        for childProject in sorted(project["childProject"], key = lambda i: i['name'] ) :

            uniqueProjectID = str(parentID) + "-" + str(childProject["id"])
            nodeDetails = {}
            nodeDetails["projectID"] = childProject["id"]
            nodeDetails["parent"] = parentID
            nodeDetails["uniqueID"] = uniqueProjectID
            nodeDetails["projectName"] = childProject["name"]
            nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(childProject["id"]) + "&tab=projectInventory"

            projectList.append( nodeDetails )

            create_project_hierarchy(childProject, uniqueProjectID, projectList, baseURL)

    return projectList

#----------------------------------------------#
def determine_application_details(baseURL, projectName, projectID, authToken):
    logger.debug("Entering determine_application_details.")
    # Create a application name for the report if the custom fields are populated
    # Default values
    applicationName = projectName
    applicationVersion = ""
    applicationPublisher = ""
    applicationDetailsString = ""

    projectInformation = CodeInsight_RESTAPIs.project.get_project_information.get_project_information_summary(baseURL, projectID, authToken)

    # Project level custom fields added in 2022R1
    if "customFields" in projectInformation:
        customFields = projectInformation["customFields"]

        # See if the custom project fields were propulated for this project
        for customField in customFields:

            # Is there the reqired custom field available?
            if customField["fieldLabel"] == "Application Name":
                if customField["value"]:
                    applicationName = customField["value"]

            # Is the custom version field available?
            if customField["fieldLabel"] == "Application Version":
                if customField["value"]:
                    applicationVersion = customField["value"]     

            # Is the custom Publisher field available?
            if customField["fieldLabel"] == "Application Publisher":
                if customField["value"]:
                    applicationPublisher = customField["value"]    



    # Join the custom values to create the application name for the report artifacts
    if applicationName != projectName:
        if applicationVersion != "":
            applicationNameVersion = applicationName + " - " + applicationVersion
        else:
            applicationNameVersion = applicationName
    else:
        applicationNameVersion = projectName

    if applicationPublisher != "":
        applicationDetailsString += "Publisher: " + applicationPublisher + " | "

    # This will either be the project name or the supplied application name
    applicationDetailsString += "Application: " + applicationName + " | "

    if applicationVersion != "":
        applicationDetailsString += "Version: " + applicationVersion
    else:
        # Rip off the  | from the end of the string if the version was not there
        applicationDetailsString = applicationDetailsString[:-3]

    applicationDetails = {}
    applicationDetails["applicationName"] = applicationName
    applicationDetails["applicationVersion"] = applicationVersion
    applicationDetails["applicationPublisher"] = applicationPublisher
    applicationDetails["applicationNameVersion"] = applicationNameVersion
    applicationDetails["applicationDetailsString"] = applicationDetailsString

    logger.info("    applicationDetails: %s" %applicationDetails)

    return applicationDetails