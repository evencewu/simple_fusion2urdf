# -*- coding: utf-8 -*-
"""
Created on Sun May 12 20:11:28 2019

@author: syuntoku
"""

import adsk, re
from xml.etree.ElementTree import Element, SubElement
from ..utils import utils

import math

class Link:

    def __init__(self, name, xyz, center_of_mass, repo, mass, inertia_tensor,stl_transform):
        """
        Parameters
        ----------
        name: str
            name of the link
        xyz: [x, y, z]
            coordinate for the visual and collision
        center_of_mass: [x, y, z]
            coordinate for the center of mass
        link_xml: str
            generated xml describing about the link
        repo: str
            the name of the repository to save the xml file
        mass: float
            mass of the link
        inertia_tensor: [ixx, iyy, izz, ixy, iyz, ixz]
            tensor of the inertia
        """
        self.name = name
        # xyz for visual
        self.xyz = [-_ for _ in xyz]  # reverse the sign of xyz
        # xyz for center of mass
        
        self.stl_transform = stl_transform
        self.center_of_mass = center_of_mass 
        self.link_xml = None
        self.repo = repo
        self.pkg_name = repo.split('/')[0]
        self.remain_repo_addr = repo[len(self.pkg_name):]
        self.mass = mass
        self.inertia_tensor = inertia_tensor
        
    def make_link_xml(self):
        #######################
        ##allOccs = root.occurrences
        ##################
        """
        Generate the link_xml and hold it by self.link_xml
        """
        
        link = Element('link')
        link.attrib = {'name':self.name}
        
        m11 = self.stl_transform.getCell(0,0)
        m12 = self.stl_transform.getCell(0,1)
        m13 = self.stl_transform.getCell(0,2)
        m21 = self.stl_transform.getCell(1,0)
        m22 = self.stl_transform.getCell(1,1)
        m23 = self.stl_transform.getCell(1,2)
        m31 = self.stl_transform.getCell(2,0)
        m32 = self.stl_transform.getCell(2,1)
        m33 = self.stl_transform.getCell(2,2)
        
        roll = math.atan2(m32, m33)
        pitch = math.atan2(-m31, math.sqrt(m32 ** 2 + m33 ** 2))
        yaw = math.atan2(m21, m11)
        #inertial
        inertial = SubElement(link, 'inertial')
        origin_i = SubElement(inertial, 'origin')
        origin_i.attrib = {'xyz':' '.join([str(_) for _ in self.center_of_mass]), 'rpy':'0 0 0'}       
        mass = SubElement(inertial, 'mass')
        mass.attrib = {'value':str(self.mass)}
        inertia = SubElement(inertial, 'inertia')
        inertia.attrib = \
            {'ixx':str(self.inertia_tensor[0]), 'iyy':str(self.inertia_tensor[1]),\
            'izz':str(self.inertia_tensor[2]), 'ixy':str(self.inertia_tensor[3]),\
            'iyz':str(self.inertia_tensor[4]), 'ixz':str(self.inertia_tensor[5])}
        
        # visual
        visual = SubElement(link, 'visual')
        origin_v = SubElement(visual, 'origin')
        origin_v.attrib = {'xyz':' '.join([str(a + b/100) for a, b in zip(self.xyz, self.stl_transform.translation.asArray())]),'rpy':str(roll) + " " + str(pitch) + " " + str(yaw)}
        geometry_v = SubElement(visual, 'geometry')
        mesh_v = SubElement(geometry_v, 'mesh')
        mesh_v.attrib = {'filename':'file://' + '$(find %s)' % self.pkg_name + self.remain_repo_addr + self.name + '.stl','scale':'0.001 0.001 0.001'}
        material = SubElement(visual, 'material')
        material.attrib = {'name':'silver'}
        
        # collision
        collision = SubElement(link, 'collision')
        origin_c = SubElement(collision, 'origin')
        origin_c.attrib = {'xyz':' '.join([str(a + b/100) for a, b in zip(self.xyz, self.stl_transform.translation.asArray())]), 'rpy':str(roll) + " " + str(pitch) + " " + str(yaw)}
        geometry_c = SubElement(collision, 'geometry')
        mesh_c = SubElement(geometry_c, 'mesh')
        mesh_c.attrib = {'filename':'file://' + '$(find %s)' % self.pkg_name + self.remain_repo_addr + self.name + '.stl','scale':'0.001 0.001 0.001'}

        # print("\n".join(utils.prettify(link).split("\n")[1:]))
        self.link_xml = "\n".join(utils.prettify(link).split("\n")[1:])

def make_inertial_dict(root, msg):
    """      
    Parameters
    ----------
    root: adsk.fusion.Design.cast(product)
        Root component
    msg: str
        Tell the status
        
    Returns
    ----------
    inertial_dict: {name:{mass, inertia, center_of_mass}}
    
    msg: str
        Tell the status
    """
    # Get component properties.      
    allOccs = root.occurrences
    inertial_dict = {}
    
    for occs in allOccs:
        # Skip the root component.
        occs_dict = {}
        prop = occs.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
        
        occs_dict['name'] = re.sub('[ :()]', '_', occs.name)

        mass = prop.mass  # kg
        occs_dict['mass'] = mass
        occs_dict['stl_transform'] = occs.transform
        center_of_mass = [_/100.0 for _ in prop.centerOfMass.asArray()] ## cm to m
        occs_dict['center_of_mass'] = center_of_mass

        # https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-ce341ee6-4490-11e5-b25b-f8b156d7cd97
        (_, xx, yy, zz, xy, yz, xz) = prop.getXYZMomentsOfInertia()
        moment_inertia_world = [_ / 10000.0 for _ in [xx, yy, zz, xy, yz, xz] ] ## kg / cm^2 -> kg/m^2
        occs_dict['inertia'] = utils.origin2center_of_mass(moment_inertia_world, center_of_mass, mass)
        
        if occs.component.name == 'base_link':
            inertial_dict['base_link'] = occs_dict
        else:
            inertial_dict[re.sub('[ :()]', '_', occs.name)] = occs_dict
        
        #msg += "Transform Type:" + str(occs.transform.translation.asArray()) + "\n"
        
        
        
    return inertial_dict, msg

