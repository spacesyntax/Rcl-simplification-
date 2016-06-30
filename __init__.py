# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RclSimplification
                                 A QGIS plugin
 This plugin simplifies a rcl map to segment map
                             -------------------
        begin                : 2016-06-20
        copyright            : (C) 2016 by Ioanna Kolovou
        email                : ioanna.kolovou@gmail.com 
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load RclSimplification class from file RclSimplification.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .rcl_simplification import RclSimplification
    return RclSimplification(iface)
