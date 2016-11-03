import java.util.ArrayList;
import java.util.HashMap;

/**
 * Created by sergeybp on 27.10.16.
 */
public class Category {

    String ctaegoryName;
    ArrayList<String> instances;
    ArrayList<Integer> extractionPatterns;
    HashMap<String, Double> promotedInstances;


    public Category(String ctaegoryName, ArrayList<String> instances, ArrayList<Integer> extractionPatterns, HashMap<String, Double> promotedInstances) {
        this.ctaegoryName = ctaegoryName;
        this.instances = instances;
        this.extractionPatterns = extractionPatterns;
        this.promotedInstances = promotedInstances;
    }

    public boolean addPromotedInstances(String instance) {
        if (instances.contains(instance)) {
            return false;
        }
        instances.add(instance);
        return true;
    }


    public boolean addPromotedPattern(Pattern pattern, PatternPool patternPoolFrom, PatternPool patternPool){
        for(Integer id: extractionPatterns){
            if(patternPool.getPatternById(id).pattern.equals(patternPoolFrom.getPatternById(pattern.id).pattern)){
                return false;
            }
        }
        extractionPatterns.add(pattern.id);
        return true;
    }

}