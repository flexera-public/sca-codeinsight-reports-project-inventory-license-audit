'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Jun 21 2023
File : report_artifacts_html.py
'''
import logging
import os
import base64

import _version

logger = logging.getLogger(__name__)

#------------------------------------------------------------------#
def generate_html_report(reportData):
    logger.info("    Entering generate_html_report")
    reportName = reportData["reportName"]
    reportFileNameBase = reportData["reportFileNameBase"]
    reportTimeStamp =  reportData["reportTimeStamp"]
    projectList = reportData["projectList"] 

    auditHistory = reportData["auditHistory"]

    scriptDirectory = os.path.dirname(os.path.realpath(__file__))
    cssFile =  os.path.join(scriptDirectory, "report_branding/css/revenera_common.css")
    logoImageFile =  os.path.join(scriptDirectory, "report_branding/images/logo_reversed.svg")
    iconFile =  os.path.join(scriptDirectory, "report_branding/images/favicon-revenera.ico")

    #########################################################
    #  Encode the image files
    encodedLogoImage = encodeImage(logoImageFile)
    encodedfaviconImage = encodeImage(iconFile)

    htmlFile = reportFileNameBase + ".html"

 #---------------------------------------------------------------------------------------------------
    # Create a simple HTML file to display
    #---------------------------------------------------------------------------------------------------
    try:
        html_ptr = open(htmlFile,"w")
    except:
        logger.error("Failed to open htmlfile %s:" %htmlFile)
        raise

    html_ptr.write("<html>\n") 
    html_ptr.write("    <head>\n")

    html_ptr.write("        <!-- Required meta tags --> \n")
    html_ptr.write("        <meta charset='utf-8'>  \n")
    html_ptr.write("        <meta name='viewport' content='width=device-width, initial-scale=1, shrink-to-fit=no'> \n")

    html_ptr.write(''' 
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.1/css/bootstrap.min.css" integrity="sha384-VCmXjywReHh4PwowAiWNagnWcLhlEJLA5buUprzK8rxFgeH0kww/aWY76TfkUoSX" crossorigin="anonymous">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.3/css/bootstrap.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.2.1/themes/default/style.min.css">
    ''')


    html_ptr.write("        <style>\n")

    # Add the contents of the css file to the head block
    try:
        f_ptr = open(cssFile)
        for line in f_ptr:
            html_ptr.write("            %s" %line)
        f_ptr.close()
    except:
        logger.error("Unable to open %s" %cssFile)
        print("Unable to open %s" %cssFile)


    html_ptr.write("        </style>\n")  

    html_ptr.write("    	<link rel='icon' type='image/png' href='data:image/png;base64, {}'>\n".format(encodedfaviconImage.decode('utf-8')))
    html_ptr.write("        <title>%s</title>\n" %(reportName.upper()))
    html_ptr.write("    </head>\n") 

    html_ptr.write("<body>\n")
    html_ptr.write("<div class=\"container-fluid\">\n")

    #---------------------------------------------------------------------------------------------------
    # Report Header
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN HEADER -->\n")
    html_ptr.write("<div class='header'>\n")
    html_ptr.write("  <div class='logo'>\n")
    html_ptr.write("    <img src='data:image/svg+xml;base64,{}' style='height: 5%;'>\n".format(encodedLogoImage.decode('utf-8')))
    html_ptr.write("  </div>\n")
    html_ptr.write("<div class='report-title'>%s</div>\n" %reportName)
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END HEADER -->\n")

    #---------------------------------------------------------------------------------------------------
    # Body of Report
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN BODY -->\n")  


    html_ptr.write("<table id='auditData' class='table table-hover table-sm row-border' style='width:90%'>\n")
    html_ptr.write("    <thead>\n")
    html_ptr.write("        <tr>\n") 
    if len(projectList) > 1:
        html_ptr.write("            <th style='width: 15%' class='text-center'>PROJECT</th>\n") 
    html_ptr.write("            <th style='width: 20%' class='text-center'>INVENTORY ITEM</th>\n")
    html_ptr.write("            <th style='width: 10%' class='text-center'>DATE</th>\n")
    html_ptr.write("            <th style='width: 15%' class='text-center'>USER</th>\n")
    html_ptr.write("            <th style='width: 15%' class='text-center'>ORIGINAL VALUE</th>\n")   
    html_ptr.write("            <th style='width: 15%' class='text-center'>NEW VALUE</th>\n") 
    html_ptr.write("        </tr>\n")
    html_ptr.write("    </thead>\n")  

    html_ptr.write("    <tbody>\n")  

    for inventoryItemID in auditHistory:
        inventoryName =  auditHistory[inventoryItemID]["inventoryItemName"]
        projectName = auditHistory[inventoryItemID]["project"]
        
        for eventID in auditHistory[inventoryItemID]["events"]:
            html_ptr.write("<tr>")
            event = auditHistory[inventoryItemID]["events"][eventID]
            
            if len(projectList) > 1:
                html_ptr.write("<td style=\"vertical-align:middle\"><a href=\"%s\" target=\"_blank\">%s</a></td>\n" %("", projectName))

            html_ptr.write("<td style=\"vertical-align:middle\"><a href=\"%s\" target=\"_blank\">%s</a></td>\n" %("", inventoryName))
            html_ptr.write("<td style=\"vertical-align:middle\">%s</td>\n" %event["date"])
            html_ptr.write("<td style=\"vertical-align:middle\">%s</td>\n" %event["user"])
            html_ptr.write("<td style=\"vertical-align:middle\">%s</td>\n" %event["oldValue"])
            html_ptr.write("<td style=\"vertical-align:middle\">%s</td>\n" %event["newValue"])
            html_ptr.write("</tr>")

    html_ptr.write("    </tbody>\n")
    html_ptr.write("</table>\n")  

    html_ptr.write("<!-- END BODY -->\n")  

    #---------------------------------------------------------------------------------------------------
    # Report Footer
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN FOOTER -->\n")
    html_ptr.write("<div class='report-footer'>\n")
    html_ptr.write("  <div style='float:right'>Generated on %s</div>\n" %reportTimeStamp)
    html_ptr.write("<br>\n")
    html_ptr.write("  <div style='float:right'>Report Version: %s</div>\n" %_version.__version__)
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END FOOTER -->\n")   

    html_ptr.write("</div>\n")
    #---------------------------------------------------------------------------------------------------
    # Add javascript 
    #---------------------------------------------------------------------------------------------------

    html_ptr.write('''

    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
    <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>  
    <script src="https://cdn.datatables.net/1.10.21/js/dataTables.bootstrap4.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@2.8.0"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.10/jstree.min.js"></script> 
    ''')

    html_ptr.write("<script>\n")

    html_ptr.write('''

            $(document).ready(function (){
                var table = $('#auditData').DataTable({
                    "order": [[ 2, "asc" ]],
                    "lengthMenu": [ [25, 50, 100, -1], [25, 50, 100, "All"] ],
                });
            });
        ''')
    

    html_ptr.write("</script>\n")

    html_ptr.write("</body>\n") 
    html_ptr.write("</html>\n") 
    html_ptr.close() 

    logger.info("    Exiting generate_html_report")
    return htmlFile




####################################################################
def encodeImage(imageFile):

    #############################################
    # Create base64 variable for branding image
    try:
        with open(imageFile,"rb") as image:
            encodedImage = base64.b64encode(image.read())
            return encodedImage
    except:
        logger.error("Unable to open %s" %imageFile)
        raise