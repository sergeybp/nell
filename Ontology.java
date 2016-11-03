import org.apache.poi.hssf.usermodel.HSSFSheet;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import ru.stachek66.nlp.mystem.holding.Factory;
import ru.stachek66.nlp.mystem.holding.MyStem;
import ru.stachek66.nlp.mystem.holding.MyStemApplicationException;
import ru.stachek66.nlp.mystem.holding.Request;
import ru.stachek66.nlp.mystem.model.Info;
import scala.Option;
import scala.collection.JavaConversions;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;

/**
 * Created by sergeybp on 27.10.16.
 */
public class Ontology {

    ArrayList<Category> instances;

    private final static MyStem mystemAnalyzer =
            new Factory("-igd --eng-gr --format json --weight")
                    .newMyStem("3.0", Option.<File>empty()).get();

    Ontology(String fileName) {
        instances = new ArrayList<>();

        try {
            readFromExcel(fileName);
        } catch (IOException e) {
            e.printStackTrace();
        } catch (MyStemApplicationException e) {
            e.printStackTrace();
        }
    }

    public void readFromExcel(String file) throws IOException, MyStemApplicationException {
        HSSFWorkbook myExcelBook = new HSSFWorkbook(new FileInputStream(file));
        HSSFSheet myExcelSheet = myExcelBook.getSheetAt(0);
        Iterator<Row> rowIterator = myExcelSheet.iterator();
        rowIterator.next();
        while (rowIterator.hasNext()) {
            Row row = rowIterator.next();
            Iterator<Cell> cellIterator = row.cellIterator();
            if (!cellIterator.hasNext()) {
                return;
            }

            // get category name
            Cell cell = cellIterator.next();
            final Iterable<Info> result =
                    JavaConversions.asJavaIterable(
                            mystemAnalyzer
                                    .analyze(Request.apply(cell.getStringCellValue()))
                                    .info()
                                    .toIterable());
            String categoryName = result.iterator().next().lex().get();

            // skip 8 cells and get seedInstances
            for (int i = 0; i < 8; i++) {
                cell = cellIterator.next();
            }
            cell = cellIterator.next();
            String toSplit = cell.getStringCellValue();
            ArrayList<String> seedInstances = new ArrayList<>();
            if (toSplit.length() > 0) {
                toSplit = toSplit.substring(1, toSplit.length() - 1);
                String[] splits = toSplit.split("\" \"");
                for (int i = 0; i < splits.length; i++) {
                    seedInstances.add(splits[i]);
                }
            }

            //get extractionPatterns
            cell = cellIterator.next();
            ArrayList<Integer> extractionPatterns = new ArrayList<>();
            toSplit = cell.getStringCellValue();
            if (toSplit.length() > 0) {
                String[] splits = toSplit.split(" ");
                for (int i = 0; i < splits.length; i++) {
                    extractionPatterns.add(Integer.parseInt(splits[i]));
                }
            }

            instances.add(new Category(categoryName, seedInstances, extractionPatterns, new HashMap<String, Double>()));
        }
    }

    public void toJson(String path){
        JSONObject obj = new JSONObject();
        for(int i = 0 ; i < instances.size(); i ++){
            JSONObject tmp = new JSONObject();
            tmp.put("categoryName", instances.get(i).ctaegoryName);
            JSONArray list = new JSONArray();
            for(String s : instances.get(i).instances){
                list.add(s);
            }
            tmp.put("seedInstances",list);
            list = new JSONArray();
            for(Integer a : instances.get(i).extractionPatterns){
                list.add(a);
            }
            tmp.put("seedExtractionPatterns",list);

            obj.put(""+i,tmp);
        }
        try {

            FileWriter file = new FileWriter(path);
            file.write(obj.toJSONString());
            file.flush();
            file.close();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }


}
