# -*- coding: utf-8 -*-
import logging
import os

from ped_parser import FamilyParser
from ped_parser.exceptions import PedigreeError

from puzzle.models import Case, Individual

from . import get_header

logger = logging.getLogger(__name__)


def get_case(variant_source, case_lines=None, case_type='ped', variant_type='snv',
            variant_mode='vcf'):
        """Create a cases and populate it with individuals

            Args:
                variant_source (str): Path to vcf files
                case_lines (Iterable): Ped like lines
                case_type (str): Format of case lines

            Returns:
                case_obj (puzzle.models.Case)
        """
        individuals = get_individuals(
            vcf=variant_source,
            case_lines=case_lines,
            case_type=case_type,
        )
        compressed = False
        tabix_index = False
        #If no individuals we still need to have a case id
        case_id = os.path.basename(variant_source)
        if variant_source.endswith('.gz'):
            compressed = True
            tabix_file = '.'.join([variant_source, 'tbi'])
            if os.path.exists(tabix_file):
                tabix_index = True
        
        for individual in individuals:
            case_id = individual.case_id

        case_obj = Case(case_id=case_id, variant_source=variant_source,
                    name=case_id, variant_type=variant_type, 
                    variant_mode=variant_mode, compressed=compressed,
                    tabix_index=tabix_index
                    )

        logger.debug("Found case with case_id: {0} and name: {1}".format(
            case_obj.case_id, case_obj.name))

        for individual in individuals:
            case_obj.add_individual(individual)

        return case_obj


def get_individuals(vcf, case_lines=None, case_type='ped'):
        """Get the individuals from a vcf file, and/or a ped file.

            Args:
                vcf (str): Path to a vcf
                case_lines(Iterable): Ped like lines
                case_type(str): Format of ped lines

            Returns:
                individuals (generator): generator with Individuals
        """
        individuals = []
        
        head = get_header(vcf)
        #Dictionary with ind_id:index where index show where in vcf ind info is
        ind_dict ={} 
        
        for index, ind in enumerate(head.individuals):
            ind_dict[ind] = index

        if case_lines:
            # read individuals from ped file
            family_parser = FamilyParser(case_lines, family_type=case_type)
            families = family_parser.families
            logger.info("Found families {0}".format(
                            ','.join(list(families.keys()))))
            if len(families) != 1:
                logger.error("Only one family can be used with vcf adapter")
                raise IOError

            case_id = list(families.keys())[0]
            logger.info("Family used in analysis: {0}".format(case_id))

            for ind_id in family_parser.individuals:
                ind = family_parser.individuals[ind_id]
                logger.info("Found individual {0}".format(ind.individual_id))
                try:
                    individual = Individual(
                        ind_id=ind_id,
                        case_id=case_id,
                        mother=ind.mother,
                        father=ind.father,
                        sex=str(ind.sex),
                        phenotype=str(ind.phenotype),
                        variant_source=vcf,
                        ind_index=ind_dict[ind_id],
                    )
                    individuals.append(individual)
                except KeyError as err:
                    #This is the case when individuals in ped does not exist 
                    #in vcf
                    raise PedigreeError(
                        family_id=case_id, 
                        individual_id=ind_id, 
                        message="Individual {0} exists in ped file but not in vcf".format(ind_id)
                    )

        else:
            case_id = os.path.basename(vcf)
            
            for ind in ind_dict:
                individual = Individual(
                    ind_id=ind,
                    case_id=case_id,
                    variant_source=vcf,
                    ind_index=ind_dict[ind]
                )
                individuals.append(individual)

                logger.debug("Found individual {0} in {1}".format(
                    ind, vcf))

        return individuals
