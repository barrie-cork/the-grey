"""
Tests for StudyAnalysisService.

Tests study analysis and synthesis functionality.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.reporting.services.study_analysis_service import StudyAnalysisService


User = get_user_model()


class TestStudyAnalysisService(TestCase):
    """Test cases for StudyAnalysisService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = StudyAnalysisService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Study Analysis Test Session',
            description='Testing study analysis features',
            owner=self.user,
            status='completed'
        )
        
        # Create tags
        self.tag_include = ReviewTag.objects.create(name='Include')
        self.tag_high_quality = ReviewTag.objects.create(name='High Quality')
        self.tag_rct = ReviewTag.objects.create(name='RCT')
        self.tag_observational = ReviewTag.objects.create(name='Observational')
        
        # Create diverse test results
        self.results = []
        for i in range(50):
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f'Study {i}: Effects of Intervention X',
                url=f'https://journal.example.com/study{i}',
                snippet=f'This study examines the effects of intervention X on outcome Y in population Z.',
                relevance_score=0.6 + (i * 0.008),
                publication_year=2020 + (i % 5),
                document_type='journal_article' if i % 3 == 0 else 'report',
                has_full_text=i % 2 == 0
            )
            self.results.append(result)
            
            # Tag included studies
            if i < 30:
                ReviewTagAssignment.objects.create(
                    result=result,
                    tag=self.tag_include,
                    assigned_by=self.user
                )
                
                # Add quality tags
                if i < 10:
                    ReviewTagAssignment.objects.create(
                        result=result,
                        tag=self.tag_high_quality,
                        assigned_by=self.user
                    )
                
                # Add study type tags
                if i % 2 == 0:
                    ReviewTagAssignment.objects.create(
                        result=result,
                        tag=self.tag_rct,
                        assigned_by=self.user
                    )
                else:
                    ReviewTagAssignment.objects.create(
                        result=result,
                        tag=self.tag_observational,
                        assigned_by=self.user
                    )
    
    def test_analyze_included_studies(self):
        """Test analysis of included studies."""
        analysis = self.service.analyze_included_studies(str(self.session.id))
        
        self.assertIsInstance(analysis, dict)
        self.assertIn('total_included', analysis)
        self.assertIn('study_characteristics', analysis)
        self.assertIn('quality_distribution', analysis)
        self.assertIn('temporal_distribution', analysis)
        self.assertIn('study_types', analysis)
        
        self.assertEqual(analysis['total_included'], 30)
        
        # Check study characteristics
        characteristics = analysis['study_characteristics']
        self.assertIn('publication_years', characteristics)
        self.assertIn('document_types', characteristics)
        self.assertIn('full_text_availability', characteristics)
    
    def test_synthesize_study_findings(self):
        """Test synthesis of study findings."""
        synthesis = self.service.synthesize_study_findings(str(self.session.id))
        
        self.assertIsInstance(synthesis, dict)
        self.assertIn('narrative_synthesis', synthesis)
        self.assertIn('thematic_analysis', synthesis)
        self.assertIn('quantitative_summary', synthesis)
        self.assertIn('evidence_strength', synthesis)
        
        # Check narrative synthesis
        narrative = synthesis['narrative_synthesis']
        self.assertIn('main_findings', narrative)
        self.assertIn('consistent_findings', narrative)
        self.assertIn('conflicting_findings', narrative)
        
        # Check evidence strength
        evidence = synthesis['evidence_strength']
        self.assertIn('overall_strength', evidence)
        self.assertIn('confidence_level', evidence)
        self.assertIn(['high', 'moderate', 'low', 'very_low'], evidence['confidence_level'])
    
    def test_perform_thematic_analysis(self):
        """Test thematic analysis of studies."""
        themes = self.service.perform_thematic_analysis(str(self.session.id))
        
        self.assertIsInstance(themes, list)
        self.assertTrue(len(themes) > 0)
        
        for theme in themes:
            self.assertIn('theme_name', theme)
            self.assertIn('description', theme)
            self.assertIn('study_count', theme)
            self.assertIn('key_studies', theme)
            self.assertIn('supporting_quotes', theme)
    
    def test_calculate_effect_sizes(self):
        """Test calculation of effect sizes (meta-analysis prep)."""
        # Add effect size data to some results
        for i in range(10):
            result = self.results[i]
            result.custom_fields = {
                'effect_size': 0.3 + (i * 0.05),
                'sample_size': 100 + (i * 20),
                'confidence_interval': [0.1, 0.5]
            }
            result.save()
        
        effect_analysis = self.service.calculate_effect_sizes(str(self.session.id))
        
        self.assertIsInstance(effect_analysis, dict)
        self.assertIn('studies_with_effect_sizes', effect_analysis)
        self.assertIn('pooled_effect_size', effect_analysis)
        self.assertIn('heterogeneity', effect_analysis)
        self.assertIn('forest_plot_data', effect_analysis)
        
        # Check forest plot data structure
        forest_data = effect_analysis['forest_plot_data']
        self.assertIsInstance(forest_data, list)
        
        for study in forest_data:
            self.assertIn('study_id', study)
            self.assertIn('effect_size', study)
            self.assertIn('confidence_interval', study)
            self.assertIn('weight', study)
    
    def test_generate_evidence_table(self):
        """Test generation of evidence summary table."""
        table = self.service.generate_evidence_table(str(self.session.id))
        
        self.assertIsInstance(table, list)
        self.assertEqual(len(table), 30)  # Only included studies
        
        for row in table:
            self.assertIn('study_id', row)
            self.assertIn('title', row)
            self.assertIn('year', row)
            self.assertIn('study_type', row)
            self.assertIn('quality_rating', row)
            self.assertIn('main_findings', row)
            self.assertIn('limitations', row)
    
    def test_assess_risk_of_bias(self):
        """Test risk of bias assessment."""
        bias_assessment = self.service.assess_risk_of_bias(str(self.session.id))
        
        self.assertIsInstance(bias_assessment, dict)
        self.assertIn('overall_risk', bias_assessment)
        self.assertIn('domain_assessments', bias_assessment)
        self.assertIn('study_level_assessments', bias_assessment)
        
        # Check domain assessments
        domains = bias_assessment['domain_assessments']
        expected_domains = [
            'selection_bias',
            'performance_bias',
            'detection_bias',
            'attrition_bias',
            'reporting_bias'
        ]
        
        for domain in expected_domains:
            self.assertIn(domain, domains)
            self.assertIn('risk_level', domains[domain])
            self.assertIn('study_count', domains[domain])
    
    def test_generate_grade_assessment(self):
        """Test GRADE assessment for evidence quality."""
        grade = self.service.generate_grade_assessment(str(self.session.id))
        
        self.assertIsInstance(grade, dict)
        self.assertIn('overall_quality', grade)
        self.assertIn('quality_factors', grade)
        self.assertIn('recommendations', grade)
        
        # Check quality factors
        factors = grade['quality_factors']
        self.assertIn('study_design', factors)
        self.assertIn('risk_of_bias', factors)
        self.assertIn('inconsistency', factors)
        self.assertIn('indirectness', factors)
        self.assertIn('imprecision', factors)
        self.assertIn('publication_bias', factors)
        
        # Check overall quality rating
        self.assertIn(grade['overall_quality'], ['high', 'moderate', 'low', 'very_low'])
    
    def test_identify_research_gaps(self):
        """Test identification of research gaps."""
        gaps = self.service.identify_research_gaps(str(self.session.id))
        
        self.assertIsInstance(gaps, list)
        
        for gap in gaps:
            self.assertIn('gap_type', gap)
            self.assertIn('description', gap)
            self.assertIn('importance', gap)
            self.assertIn('recommendations', gap)
            self.assertIn(['high', 'medium', 'low'], gap['importance'])
    
    def test_generate_implications_summary(self):
        """Test generation of implications summary."""
        implications = self.service.generate_implications_summary(str(self.session.id))
        
        self.assertIsInstance(implications, dict)
        self.assertIn('clinical_implications', implications)
        self.assertIn('policy_implications', implications)
        self.assertIn('research_implications', implications)
        self.assertIn('practice_recommendations', implications)
        
        # Check practice recommendations
        recommendations = implications['practice_recommendations']
        self.assertIsInstance(recommendations, list)
        
        for rec in recommendations:
            self.assertIn('recommendation', rec)
            self.assertIn('strength', rec)
            self.assertIn('evidence_basis', rec)
    
    def test_calculate_publication_bias(self):
        """Test calculation of publication bias indicators."""
        bias = self.service.calculate_publication_bias(str(self.session.id))
        
        self.assertIsInstance(bias, dict)
        self.assertIn('funnel_plot_asymmetry', bias)
        self.assertIn('small_study_effects', bias)
        self.assertIn('grey_literature_proportion', bias)
        self.assertIn('bias_risk_assessment', bias)
        
        # Check grey literature proportion
        grey_lit = bias['grey_literature_proportion']
        self.assertGreaterEqual(grey_lit, 0)
        self.assertLessEqual(grey_lit, 1)
    
    def test_generate_summary_of_findings(self):
        """Test generation of summary of findings table."""
        summary = self.service.generate_summary_of_findings(str(self.session.id))
        
        self.assertIsInstance(summary, dict)
        self.assertIn('outcomes', summary)
        self.assertIn('certainty_assessment', summary)
        self.assertIn('effect_estimates', summary)
        self.assertIn('interpretation', summary)
        
        # Check outcomes
        outcomes = summary['outcomes']
        self.assertIsInstance(outcomes, list)
        
        for outcome in outcomes:
            self.assertIn('outcome_name', outcome)
            self.assertIn('studies_count', outcome)
            self.assertIn('participants_total', outcome)
            self.assertIn('effect_estimate', outcome)
            self.assertIn('certainty', outcome)
    
    def test_export_analysis_visualizations(self):
        """Test export of analysis visualizations data."""
        viz_data = self.service.export_analysis_visualizations(str(self.session.id))
        
        self.assertIsInstance(viz_data, dict)
        self.assertIn('forest_plot', viz_data)
        self.assertIn('funnel_plot', viz_data)
        self.assertIn('risk_of_bias_plot', viz_data)
        self.assertIn('evidence_network', viz_data)
        
        # Check that visualization data is properly formatted
        forest = viz_data['forest_plot']
        self.assertIn('data', forest)
        self.assertIn('layout', forest)
        self.assertIn('config', forest)
    
    def test_analysis_with_no_included_studies(self):
        """Test analysis when no studies are included."""
        empty_session = SearchSession.objects.create(
            title='Empty Analysis Session',
            description='No included studies',
            owner=self.user,
            status='completed'
        )
        
        analysis = self.service.analyze_included_studies(str(empty_session.id))
        
        self.assertEqual(analysis['total_included'], 0)
        self.assertIn('message', analysis)
        self.assertIn('no studies', analysis['message'].lower())
    
    def test_logging_in_analysis(self):
        """Test that analysis operations are properly logged."""
        with self.assertLogs('apps.reporting.services.study_analysis_service', level='INFO') as cm:
            self.service.analyze_included_studies(str(self.session.id))
        
        self.assertTrue(any('Analyzing included studies' in msg for msg in cm.output))
        self.assertTrue(any('Analysis completed' in msg for msg in cm.output))